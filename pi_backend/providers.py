import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List
from urllib.parse import urlparse

from openai import OpenAI


class LLMProvider(ABC):
    @abstractmethod
    def embedding(self, text: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def answer(
        self,
        question: str,
        contexts: List[dict],
        recent_messages: list[dict] | None = None,
        memory_summary: str | None = None,
        max_output_tokens: int | None = None,
    ) -> "ProviderAnswer":
        raise NotImplementedError

    @abstractmethod
    def generate_conversation_title(self, question: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def summarize_messages(self, messages: list[dict], previous_summary: str | None = None) -> str:
        raise NotImplementedError


@dataclass
class ProviderAnswer:
    text: str
    usage: dict[str, Any]


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.client = OpenAI()
        self.model = os.getenv("CHAT_MODEL", "gpt-5-mini")
        self.embed_model = os.getenv("EMBED_MODEL", "text-embedding-3-small")
        self.reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", "minimal")
        self.verbosity = os.getenv("OPENAI_TEXT_VERBOSITY", "medium")

    def embedding(self, text: str) -> list[float]:
        return self.client.embeddings.create(model=self.embed_model, input=text).data[0].embedding

    def answer(
        self,
        question: str,
        contexts: List[dict],
        recent_messages: list[dict] | None = None,
        memory_summary: str | None = None,
        max_output_tokens: int | None = None,
    ) -> ProviderAnswer:
        blocks = []
        for i, ctx in enumerate(contexts, start=1):
            blocks.append(
                f"[Source {i}]\nURL: {ctx['url']}\nChunk ID: {ctx['chunk_id']}\n\n{ctx['text']}"
            )

        history_lines = []
        for message in (recent_messages or []):
            role = message.get("role", "user")
            content = message.get("content", "").strip()
            if content:
                history_lines.append(f"- {role}: {content}")

        prompt = f"""
You are Beisser AI, an intelligent assistant for the DMSI Agility documentation.

Answer the user's question accurately using ONLY the provided documentation excerpts.
If the answer is not found in the sources, say so clearly.

Write the answer in clean, professional Markdown. Use headings, bullet points, and bold text sparingly to make the content easy to scan. Avoid repetitive structure or formulaic headers like "Short Answer" or "Key Details" unless they naturally fit the content.

Formatting rules:
- Provide a direct and helpful response.
- Use bullet points or numbered steps for procedures.
- Bold important terms, labels, or warnings.
- Keep paragraphs short and concise.
- If the documentation is ambiguous or incomplete, say that plainly.
- When citing where information came from, reference the relevant source numbers like `(Source 1)`.
- Do not invent features, settings, or steps that are not supported by the provided excerpts.
- End with 2-4 practical and relevant follow-up questions under `## Related Questions`.
- Do not include a separate Sources section in your answer.

Conversation memory summary:
{memory_summary or 'No summary available.'}

Recent conversation turns:
{chr(10).join(history_lines) if history_lines else '- No recent turns available.'}

Question:
{question}

Documentation Sources:
{chr(10).join(blocks)}
"""

        payload: dict[str, Any] = {
            "model": self.model,
            "input": prompt,
        }
        if self.model.startswith("gpt-5"):
            payload["reasoning"] = {"effort": self.reasoning_effort}
            payload["text"] = {"verbosity": self.verbosity}
        if max_output_tokens:
            payload["max_output_tokens"] = max_output_tokens

        response = self.client.responses.create(**payload)
        return ProviderAnswer(
            text=self._append_sources_section(response.output_text, contexts),
            usage=getattr(response, "usage", {}) or {},
        )

    def _append_sources_section(self, answer: str, contexts: List[dict]) -> str:
        seen_urls = set()
        source_lines = []

        for index, ctx in enumerate(contexts, start=1):
            url = ctx.get("url", "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            source_lines.append(f"- [Source {index}: {self._source_label(url)}]({url})")

        if not source_lines:
            return answer

        return f"{answer.rstrip()}\n\n## Sources\n" + "\n".join(source_lines)

    def _source_label(self, url: str) -> str:
        parsed = urlparse(url)
        host = parsed.netloc or "documentation"
        path = parsed.path.strip("/")
        if not path:
            return host
        tail = path.split("/")[-1]
        return f"{host} / {tail[:50]}"

    def generate_conversation_title(self, question: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=f"""
Create a short conversation title for this user request.

Rules:
- 3 to 7 words.
- No quotation marks.
- No punctuation at the end.
- Prefer title case when natural.
- Be specific to the topic.

User request:
{question}
""",
        )
        title = response.output_text.strip().strip('"').strip("'")
        return title[:80] or "New conversation"

    def summarize_messages(self, messages: list[dict], previous_summary: str | None = None) -> str:
        compact_messages = []
        for message in messages[-12:]:
            role = message.get("role", "user")
            content = message.get("content", "").strip()
            if content:
                compact_messages.append(f"- {role}: {content}")

        response = self.client.responses.create(
            model=self.model,
            input=f"""
Summarize the conversation state for memory compression.
Keep it factual and concise (max 120 words).
Capture user goals, constraints, and unresolved questions.

Previous summary:
{previous_summary or 'None'}

Recent turns:
{chr(10).join(compact_messages) if compact_messages else '- None'}
""",
        )
        return response.output_text.strip()
