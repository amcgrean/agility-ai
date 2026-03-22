"""Teams bot that routes messages to the Agility AI /ask endpoint.

The bot strips @mention prefixes, forwards the question to the backend,
and returns the answer with optional follow-up suggestions formatted as
markdown (Teams renders markdown in bot messages).
"""

import logging
import os
import re

import aiohttp
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import Activity, ActivityTypes

logger = logging.getLogger(__name__)

AGILITY_API_URL = os.getenv("AGILITY_API_URL", "http://localhost:8000")
API_REQUEST_TIMEOUT = int(os.getenv("BOT_API_TIMEOUT_SECONDS", "30"))

# Pattern to strip Teams @mention XML tags from the message text
MENTION_PATTERN = re.compile(r"<at>[^<]*</at>\s*")


def _strip_mentions(text: str) -> str:
    return MENTION_PATTERN.sub("", text).strip()


class AgilityBot(ActivityHandler):
    """Beisser AI Teams bot — answers questions from the indexed document corpus."""

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        raw_text = (turn_context.activity.text or "").strip()
        question = _strip_mentions(raw_text)

        if not question:
            await turn_context.send_activity(
                "Hi! Ask me anything about Agility software, lumber operations, or company procedures."
            )
            return

        # Send typing indicator while we fetch the answer
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))

        from_prop = turn_context.activity.from_property
        user_id = (from_prop.id if from_prop else None) or "teams-user"

        try:
            answer, follow_ups = await self._fetch_answer(question, user_id)
        except Exception:
            logger.exception("Agility AI API call failed")
            await turn_context.send_activity(
                "Sorry, I couldn't reach the knowledge base right now. Please try again in a moment."
            )
            return

        reply = answer
        if follow_ups:
            bullets = "\n".join(f"- {q}" for q in follow_ups[:3])
            reply += f"\n\n**You might also ask:**\n{bullets}"

        await turn_context.send_activity(reply)

    async def on_members_added_activity(self, members_added, turn_context: TurnContext) -> None:
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    "Hello! I'm the **Beisser AI** assistant. "
                    "Ask me anything about Agility software, lumber operations, or company procedures."
                )

    async def _fetch_answer(self, question: str, user_id: str) -> tuple[str, list[str]]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{AGILITY_API_URL}/ask",
                json={"question": question},
                headers={"X-User-Identity": user_id},
                timeout=aiohttp.ClientTimeout(total=API_REQUEST_TIMEOUT),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

        answer = data.get("answer") or "No answer available."
        follow_ups = data.get("followUpQuestions") or []
        return answer, follow_ups
