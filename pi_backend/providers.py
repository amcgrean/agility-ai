import os
from abc import ABC, abstractmethod
from typing import List
from urllib.parse import urlparse

from openai import OpenAI


class LLMProvider(ABC):
    @abstractmethod
    def answer(self, question: str, contexts: List[dict]) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_conversation_title(self, question: str) -> str:
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.client = OpenAI()
        self.model = os.getenv("CHAT_MODEL", "gpt-5-mini")

    def answer(self, question: str, contexts: List[dict]) -> str:
        blocks = []
        for i, ctx in enumerate(contexts, start=1):
            blocks.append(
                f"[Source {i}]\nURL: {ctx['url']}\nChunk ID: {ctx['chunk_id']}\n\n{ctx['text']}"
            )

        prompt = f"""
You are an assistant for the DMSI Agility documentation.

Answer the user's question using ONLY the provided documentation excerpts.
If the answer is not found in the sources, say so clearly.

Write the answer in clean Markdown that is easy to scan, similar to a polished product guide.

Use this structure when the answer is available:
- `## Short Answer`
- `## Key Details`
- `## Related Questions` with 2-4 practical follow-up questions

Formatting rules:
- Start with a short direct answer or summary under `## Short Answer`.
- Use `## Key Details` for the main explanation.
- Use bullet points or numbered steps for procedures.
- Bold important terms, labels, or warnings.
- Keep paragraphs short.
- If the documentation is ambiguous or incomplete, say that plainly.
- When citing where information came from, reference the relevant source numbers like `(Source 1)`.
- Do not invent features, settings, or steps that are not supported by the provided excerpts.
- Keep those follow-up questions practical and relevant, not generic.
- Do not include a separate Sources section in your answer.

Question:
{question}

Documentation Sources:
{chr(10).join(blocks)}
"""

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        return self._append_sources_section(response.output_text, contexts)

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
