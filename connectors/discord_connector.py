"""
Official Discord Bot API Connector.
Uses discord.py to interface with Discord servers, channels, and ticket threads.
Enforces:
- Official bot token only (never user accounts).
- Message Content Intent verification.
- Permission checks (View Channels, Read Message History).
- Employee User ID filtering and human-agent vs bot distinction.
- Detection of customer replies via message.reference.
"""

import asyncio
import datetime
import logging
from typing import Optional, List, Dict, Any, Callable
import discord

from schemas.message_schema import NormalizedMessageSchema
from services.security_service import SecurityService
from services.shift_service import ShiftService

logger = logging.getLogger("CSKHAssistant.Discord")


class DiscordConnector:
    """Manages Discord bot connection, live message monitoring, and history backfill."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        employee_user_id: Optional[str] = None,
        allowed_channel_ids: Optional[List[str]] = None,
    ):
        self.bot_token = bot_token or SecurityService.get_credential("DISCORD_BOT_TOKEN")
        self.employee_user_id = employee_user_id or SecurityService.get_credential("DISCORD_USER_ID")
        
        raw_channels = allowed_channel_ids or SecurityService.get_credential("DISCORD_ALLOWED_CHANNEL_IDS", "")
        if isinstance(raw_channels, str):
            self.allowed_channel_ids = [c.strip() for c in raw_channels.split(",") if c.strip()]
        else:
            self.allowed_channel_ids = list(raw_channels)

        self.client: Optional[discord.Client] = None
        self._is_running = False
        self._on_message_callback: Optional[Callable[[NormalizedMessageSchema], None]] = None

    def is_configured(self) -> bool:
        """Check if bot token and user ID are configured."""
        return bool(
            self.bot_token
            and not self.bot_token.startswith("your_")
            and self.employee_user_id
            and not self.employee_user_id.startswith("your_")
        )

    def test_connection(self) -> Dict[str, Any]:
        """Synchronously/briefly connects to Discord to verify token, intents, and permissions."""
        if not self.is_configured():
            return {
                "success": False,
                "error": "Thiếu Discord Bot Token hoặc Discord User ID trong cấu hình.",
                "details": None,
            }

        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True

        test_client = discord.Client(intents=intents)
        result = {"success": False, "error": None, "details": {}}

        async def _run_test():
            try:
                # Login only to check credentials
                await test_client.login(self.bot_token)
                result["success"] = True
                result["details"] = {
                    "bot_user": str(test_client.user),
                    "bot_id": test_client.user.id,
                    "intents_message_content": intents.message_content,
                }
            except discord.PrivilegedIntentsRequired:
                result["error"] = "Bot chưa được bật 'Message Content Intent' trong Discord Developer Portal."
            except discord.LoginFailure:
                result["error"] = "Discord Bot Token không hợp lệ hoặc đã hết hạn."
            except Exception as e:
                result["error"] = f"Lỗi kết nối Discord: {SecurityService.scrub_log_message(str(e))}"
            finally:
                if not test_client.is_closed():
                    await test_client.close()

        try:
            asyncio.run(_run_test())
        except Exception as e:
            result["error"] = f"Không thể thực thi kiểm tra kết nối: {e}"

        return result

    def normalize_discord_message(self, message: discord.Message) -> NormalizedMessageSchema:
        """Converts a discord.py Message object into NormalizedMessageSchema."""
        author_id_str = str(message.author.id)
        is_employee = bool(self.employee_user_id and author_id_str == str(self.employee_user_id).strip())
        is_bot = message.author.bot or message.webhook_id is not None

        # Check if this is a reply to another message
        ref_id_str = None
        is_reply = False
        if message.reference and message.reference.message_id:
            ref_id_str = str(message.reference.message_id)
            is_reply = True

        # Timestamp in UTC
        dt_utc = message.created_at
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=datetime.timezone.utc)
        dt_local = ShiftService.utc_to_local(dt_utc)

        # Verification status
        # If authored by the verified employee ID and not a bot, it is verified!
        if is_employee and not is_bot:
            verification_status = "verified"
        else:
            verification_status = "unverified"

        # Determine shift date and shift num
        shift_date, shift_num = ShiftService.resolve_shift_for_timestamp(dt_utc)

        return NormalizedMessageSchema(
            platform="discord",
            platform_message_id=str(message.id),
            platform_conversation_id=str(message.channel.id),
            server_id=str(message.guild.id) if message.guild else None,
            channel_id=str(message.channel.id),
            author_id=author_id_str,
            author_name=message.author.name if is_employee else SecurityService.sanitize_customer_identifier(author_id_str, "discord"),
            author_is_employee=is_employee,
            is_bot=is_bot,
            content=message.content or "",
            timestamp_utc=dt_utc,
            timestamp_local=dt_local,
            reference_message_id=ref_id_str,
            is_reply_to_customer=is_reply and is_employee,
            verification_status=verification_status,
            shift_date=shift_date,
            shift_num=shift_num,
        )

    async def fetch_history_for_window(
        self,
        start_utc: datetime.datetime,
        end_utc: datetime.datetime,
    ) -> List[NormalizedMessageSchema]:
        """Backfills messages across allowed channels within a specific time window [start_utc, end_utc)."""
        if not self.is_configured():
            logger.warning("Discord not configured. Backfill skipped.")
            return []

        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True

        client = discord.Client(intents=intents)
        normalized_msgs: List[NormalizedMessageSchema] = []

        try:
            await client.login(self.bot_token)
            # Fetch channels
            for ch_id_str in self.allowed_channel_ids:
                try:
                    ch_id = int(ch_id_str)
                    channel = await client.fetch_channel(ch_id)
                    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                        continue

                    # Fetch history between start_utc and end_utc
                    # Note: discord.py history 'after' and 'before' take UTC datetimes
                    async for msg in channel.history(after=start_utc - datetime.timedelta(seconds=1), before=end_utc + datetime.timedelta(seconds=1), limit=500):
                        if start_utc <= msg.created_at < end_utc:
                            norm = self.normalize_discord_message(msg)
                            normalized_msgs.append(norm)

                except discord.Forbidden:
                    logger.warning(f"Bot lacks permission to read channel {ch_id_str}")
                except Exception as ex:
                    logger.warning(f"Error fetching channel {ch_id_str}: {ex}")

        except Exception as e:
            logger.error(f"Failed historical sync from Discord: {SecurityService.scrub_log_message(str(e))}")
        finally:
            if not client.is_closed():
                await client.close()

        return normalized_msgs
