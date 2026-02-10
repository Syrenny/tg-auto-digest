from loguru import logger

from telegram_radar.models import Batch, Comment, Post, PostPayload


def _metadata_text(post: Post) -> str:
    return (
        f"[{post.channel_title}] {post.permalink}\n"
        f"Date: {post.date.isoformat()}\n\n"
    )


def _comment_text(comment: Comment) -> str:
    author = comment.author_name or "Anonymous"
    return f"\n--- Comment by {author} ---\n{comment.text}\n"


class BatchBuilder:
    def build_batches(
        self,
        posts: list[Post],
        max_chars_per_batch: int,
    ) -> list[Batch]:
        payloads: list[PostPayload] = []

        for post in posts:
            meta = _metadata_text(post)
            base_chars = len(meta) + len(post.text)

            if base_chars > max_chars_per_batch:
                logger.warning(
                    "Skipping post {} in '{}' — {} chars exceeds batch budget {}",
                    post.id,
                    post.channel_title,
                    base_chars,
                    max_chars_per_batch,
                )
                continue

            included_comments: list[Comment] = []
            total_chars = base_chars
            for comment in post.comments:
                ct = _comment_text(comment)
                if total_chars + len(ct) > max_chars_per_batch:
                    break
                included_comments.append(comment)
                total_chars += len(ct)

            payloads.append(
                PostPayload(
                    post=post,
                    comments=included_comments,
                    char_count=total_chars,
                )
            )

        batches: list[Batch] = []
        current_payloads: list[PostPayload] = []
        current_chars = 0

        for payload in payloads:
            if (
                current_payloads
                and current_chars + payload.char_count > max_chars_per_batch
            ):
                batches.append(_make_batch(current_payloads, current_chars))
                current_payloads = []
                current_chars = 0

            current_payloads.append(payload)
            current_chars += payload.char_count

        if current_payloads:
            batches.append(_make_batch(current_payloads, current_chars))

        for i, batch in enumerate(batches):
            logger.info(
                "Batch {}: {} posts, {} comments, {} chars",
                i + 1,
                batch.post_count,
                batch.comment_count,
                batch.total_chars,
            )

        return batches


def _make_batch(
    payloads: list[PostPayload], total_chars: int
) -> Batch:
    return Batch(
        payloads=payloads,
        total_chars=total_chars,
        post_count=len(payloads),
        comment_count=sum(len(p.comments) for p in payloads),
    )
