import time

import instructor
from loguru import logger
from openai import AsyncOpenAI

from telegram_radar.models import Batch, DigestBatchResult
from telegram_radar.settings import Settings


def _format_batch_prompt(batch: Batch) -> str:
    parts: list[str] = []
    for payload in batch.payloads:
        post = payload.post
        parts.append(
            f"=== POST from [{post.channel_title}] ===\n"
            f"Date: {post.date.isoformat()}\n"
            f"URL: {post.permalink}\n"
            f"Text:\n{post.text}\n"
        )
        for comment in payload.comments:
            author = comment.author_name or "Anonymous"
            link_part = f" ({comment.link})" if comment.link else ""
            parts.append(
                f"  -- Comment by {author}{link_part}:\n"
                f"  {comment.text}\n"
            )
    return "\n".join(parts)


SYSTEM_PROMPT = """\
You are a digest assistant. Analyze the Telegram channel posts below \
and produce a structured digest.

Rules:
- Extract real deadlines from the text; if none exist, omit the deadline field.
- post_quote MUST be a verbatim substring from the post text (max 160 chars).
- comment_quote MUST be a verbatim substring from a comment (max 160 chars), \
or null if no comment is noteworthy.
- source_url MUST be the URL of the original post. If the key insight is from \
a comment and a comment link is available, use that instead.
- priority: 0.0 = low relevance, 1.0 = highest urgency/importance.
- date: the post date in YYYY-MM-DD format.
- batch_summary: 1-3 sentences summarizing the overall batch.
"""


class LLMSummarizer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = instructor.from_openai(
            AsyncOpenAI(api_key=settings.llm_api_key)
        )

    async def summarize_batch(self, batch: Batch) -> DigestBatchResult:
        prompt = _format_batch_prompt(batch)
        start = time.monotonic()

        result = await self._client.chat.completions.create(
            model=self._settings.llm_model,
            response_model=DigestBatchResult,
            max_retries=3,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        elapsed = time.monotonic() - start
        logger.info(
            "LLM summarized batch ({} posts) in {:.1f}s → {} items",
            batch.post_count,
            elapsed,
            len(result.items),
        )
        return result

    async def check_health(self) -> bool:
        try:
            raw = instructor.from_openai(
                AsyncOpenAI(api_key=self._settings.llm_api_key)
            )
            await raw.chat.completions.create(
                model=self._settings.llm_model,
                response_model=None,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False
