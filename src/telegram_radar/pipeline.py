from loguru import logger

from telegram_radar.batch_builder import BatchBuilder
from telegram_radar.digest_builder import DigestBuilder
from telegram_radar.models import Post
from telegram_radar.protocols import StateRepository, Summarizer, TelegramGateway
from telegram_radar.settings import Settings


async def run_digest(
    gateway: TelegramGateway,
    batch_builder: BatchBuilder,
    summarizer: Summarizer,
    digest_builder: DigestBuilder,
    state: StateRepository,
    settings: Settings,
) -> str:
    logger.info("Starting digest run")
    state.load()

    channels = await gateway.get_radar_channels()
    if not channels:
        logger.error("No channels found in '{}' folder", settings.radar_folder_name)
        return (
            f"Error: No channels found in '{settings.radar_folder_name}' folder."
        )

    all_posts: list[Post] = []
    parsed_names: list[str] = []

    for ch in channels:
        last_id = state.get_last_message_id(ch.id)
        posts = await gateway.fetch_posts(
            channel=ch,
            since_message_id=last_id,
            since_hours=settings.fetch_since_hours,
            limit=settings.fetch_limit_per_channel,
        )

        for post in posts:
            comments = await gateway.fetch_comments(
                channel=ch,
                post=post,
                limit=settings.comments_limit_per_post,
                max_comment_len=settings.comment_max_len,
            )
            post.comments = comments

        all_posts.extend(posts)
        parsed_names.append(ch.title)

        if posts:
            max_id = max(p.id for p in posts)
            state.update_channel(ch.id, max_id, len(posts))

    logger.info(
        "Fetched {} posts across {} channels",
        len(all_posts),
        len(channels),
    )

    if not all_posts:
        state.record_last_run(channels_parsed=parsed_names)
        state.save()
        return "No new posts found in Radar channels since last check."

    batches = batch_builder.build_batches(
        all_posts, settings.llm_max_chars_per_batch
    )
    logger.info("Built {} batches", len(batches))

    batch_results = []
    for i, batch in enumerate(batches):
        logger.info("Summarizing batch {}/{}", i + 1, len(batches))
        result = await summarizer.summarize_batch(batch)
        batch_results.append(result)

    digest = digest_builder.build_digest(
        batch_results,
        max_items=settings.digest_max_items,
        urgent_days=settings.deadline_urgent_days,
    )

    state.record_last_run(channels_parsed=parsed_names)
    state.save()

    logger.info("Digest run complete")
    return digest
