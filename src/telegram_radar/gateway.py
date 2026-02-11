from datetime import datetime, timedelta, timezone

from loguru import logger
from telethon import TelegramClient, functions

from telegram_radar.models import ChannelInfo, Comment, Post
from telegram_radar.settings import Settings


def _build_permalink(channel: ChannelInfo, message_id: int) -> str:
    if channel.username:
        return f"https://t.me/{channel.username}/{message_id}"
    cid = str(channel.id)
    if cid.startswith("-100"):
        cid = cid[4:]
    return f"https://t.me/c/{cid}/{message_id}"


class TelegramClientGateway:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = TelegramClient(
            str(settings.telethon_session_path),
            settings.telegram_api_id,
            settings.telegram_api_hash,
        )

    async def connect(self) -> None:
        await self._client.connect()
        logger.info("Telethon connected")

    async def is_authorized(self) -> bool:
        try:
            authorized = await self._client.is_user_authorized()
        except Exception:
            logger.warning("Session check failed, treating as unauthorized")
            return False
        logger.info("Session authorized: {}", authorized)
        return authorized

    async def send_code(self, phone: str) -> None:
        await self._client.send_code_request(phone)
        logger.info("Code sent to {}", phone)

    async def sign_in_code(self, phone: str, code: str) -> None:
        await self._client.sign_in(phone, code=code)
        logger.info("Sign-in successful")

    async def sign_in_password(self, password: str) -> None:
        await self._client.sign_in(password=password)
        logger.info("Sign-in with 2FA successful")

    async def log_out(self) -> None:
        try:
            await self._client.log_out()
        except Exception as e:
            logger.warning("Logout failed: {}, proceeding with client recreation", e)
        try:
            await self._client.disconnect()
        except Exception:
            pass
        self._client = TelegramClient(
            str(self._settings.telethon_session_path),
            self._settings.telegram_api_id,
            self._settings.telegram_api_hash,
        )
        await self._client.connect()
        logger.info("Session logged out and client reconnected")

    async def stop(self) -> None:
        await self._client.disconnect()
        logger.info("Telethon client disconnected")

    async def check_health(self) -> bool:
        try:
            await self._client.get_me()
            return True
        except Exception:
            return False

    async def get_radar_channels(self) -> list[ChannelInfo]:
        result = await self._client(
            functions.messages.GetDialogFiltersRequest()
        )
        folder_name = self._settings.radar_folder_name
        channels: list[ChannelInfo] = []

        for f in result.filters:
            if not hasattr(f, "title"):
                continue
            title_text = (
                f.title.text if hasattr(f.title, "text") else str(f.title)
            )
            if title_text != folder_name:
                continue

            for peer in f.include_peers:
                try:
                    entity = await self._client.get_entity(peer)
                    channels.append(
                        ChannelInfo(
                            id=entity.id,
                            title=getattr(entity, "title", str(entity.id)),
                            username=getattr(entity, "username", None),
                        )
                    )
                except Exception:
                    logger.warning("Failed to resolve peer {}", peer)
            break

        logger.info("Discovered {} channels in '{}'", len(channels), folder_name)
        return channels

    async def fetch_posts(
        self,
        channel: ChannelInfo,
        since_message_id: int | None,
        since_hours: int,
        limit: int,
    ) -> list[Post]:
        entity = await self._client.get_entity(channel.id)
        kwargs: dict = {"limit": limit}

        if since_message_id is not None:
            kwargs["min_id"] = since_message_id
        else:
            kwargs["offset_date"] = datetime.now(timezone.utc) - timedelta(
                hours=since_hours
            )

        posts: list[Post] = []
        async for msg in self._client.iter_messages(entity, **kwargs):
            if not msg.text:
                continue
            posts.append(
                Post(
                    id=msg.id,
                    channel_id=channel.id,
                    channel_title=channel.title,
                    channel_username=channel.username,
                    date=msg.date,
                    text=msg.text,
                    permalink=_build_permalink(channel, msg.id),
                )
            )

        logger.info(
            "Fetched {} posts from '{}'", len(posts), channel.title
        )
        return posts

    async def fetch_comments(
        self,
        channel: ChannelInfo,
        post: Post,
        limit: int,
        max_comment_len: int,
    ) -> list[Comment]:
        try:
            entity = await self._client.get_entity(channel.id)
            # Check if post has replies
            msg = await self._client.get_messages(entity, ids=post.id)
            if not msg or not getattr(msg, "replies", None):
                return []
            if msg.replies.replies == 0:
                return []

            comments: list[Comment] = []
            async for reply in self._client.iter_messages(
                entity, reply_to=post.id, limit=limit
            ):
                if not reply.text:
                    continue
                text = reply.text[:max_comment_len]
                sender_name = None
                if reply.sender:
                    sender_name = getattr(
                        reply.sender,
                        "first_name",
                        getattr(reply.sender, "title", None),
                    )
                comment_link = None
                if getattr(msg.replies, "channel_id", None):
                    comment_link = (
                        f"https://t.me/c/{msg.replies.channel_id}/{reply.id}"
                    )
                comments.append(
                    Comment(
                        id=reply.id,
                        author_name=sender_name,
                        date=reply.date,
                        text=text,
                        link=comment_link,
                    )
                )

            return comments
        except Exception:
            logger.debug(
                "Could not fetch comments for post {} in '{}'",
                post.id,
                channel.title,
            )
            return []
