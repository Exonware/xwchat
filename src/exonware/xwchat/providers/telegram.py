#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/telegram.py
Telegram chat provider implementation.

Group and channel listening:
- Groups: the bot only receives messages that @mention it (or are replies to it) unless Privacy Mode
  is disabled in @BotFather: /setprivacy -> select bot -> Disable. After changing, re-add the bot to
  the group if it was added before.
- Channels: the bot only receives channel_post updates when it is added as an Administrator.
"""

from typing import Any, AsyncIterator, Callable
import asyncio
import logging
from exonware.xwsystem.io.serialization import JsonSerializer
import os
import signal
import sys
import csv
from datetime import datetime
from pathlib import Path
from exonware.xwsystem import get_logger
from exonware.xwsystem.utils.web import extract_webpage_text
from ..base import AChatProvider
from ..defs import ChatCapability, ChatProviderType, MessageContext
from ..errors import XWChatConnectionError, XWChatProviderError
logger = get_logger(__name__)
# Standard imports - NO try/except!
# These should be declared as dependencies in pyproject.toml
from telegram import Bot, Update, MessageEntity
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest, TelegramError, NetworkError


def _telegram_plain_from_entities(text: str) -> str:
    """Best-effort plain text when parse_mode fails (strip simple HTML tags, unescape entities)."""
    import re
    import html as html_module

    t = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    t = re.sub(r"</p\s*>", "\n", t, flags=re.IGNORECASE)
    t = re.sub(r"<[^>]+>", "", t)
    return html_module.unescape(t)


def _merge_send_kwargs(send_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Defaults for long bot replies (Telegram Bot API)."""
    out = dict(send_kwargs)
    if out.get("parse_mode") and "disable_web_page_preview" not in out:
        out["disable_web_page_preview"] = True
    return out


def _strip_bot_mention(text: str, bot_username: str) -> str:
    """Remove @bot_username from text (case-insensitive), then strip and normalize spaces."""
    if not text or not bot_username:
        return (text or "").strip()
    mention = "@" + bot_username
    out = text
    while True:
        i = out.lower().find(mention.lower())
        if i == -1:
            break
        out = (out[:i] + out[i + len(mention) :]).strip()
    return " ".join(out.split())


def user_exists(username: str) -> bool:
    """
    Check if a Telegram username exists by web scraping.
    This is the single function for checking Telegram username existence.
    Uses xwsystem extract_webpage_text to fetch and extract text from t.me/<username>.
    Args:
        username: Telegram username (with or without @)
    Returns:
        True if user exists, False otherwise
    Examples:
        >>> user_exists("muhdashe")
        True
        >>> user_exists("@muhdashe")
        True
        >>> user_exists("nonexistent_user_12345")
        False
    """
    username = username.lstrip('@').strip()
    if not username:
        return False
    try:
        url = f"https://t.me/{username}"
        text = extract_webpage_text(url)
        # Check for "Send Message" which indicates user exists
        if "Send Message" in text:
            return True
        if "Download\nIf" in text:
            return False
        if "Download" in text and "If you have" in text:
            download_pos = text.find("Download")
            if_pos = text.find("If you have")
            if download_pos > 0 and if_pos > 0 and abs(download_pos - if_pos) < 100:
                return False
        return username.lower() in text.lower()
    except Exception as e:
        logger.warning("Error checking if Telegram username exists via web: %s", e)
        return False


class TelegramChatProvider(AChatProvider):
    """Telegram chat provider implementation."""

    def __init__(self, api_token: str, bot_name: str | None = None, storage_path: str | None = None, auto_save_users: bool = True, agent_id: str | None = None, data_path: str | None = None, enable_message_logging: bool = True, storage_connection: Any | None = None, connection_cache_path: (str | Path) | None = None, proxy_url: str | None = None):
        """
        Initialize Telegram provider.
        Args:
            api_token: Telegram Bot API token
            bot_name: Optional bot name (defaults to 'telegram')
            storage_path: Optional path to store user data (defaults based on agent_id and data_path)
            auto_save_users: Whether to automatically save user info when they send messages (default: True)
            agent_id: Optional agent ID for organizing data (defaults to 'default')
            data_path: Optional base data path (defaults to xwchat/data/xwchat)
            enable_message_logging: Whether to log all messages to CSV (default: True)
            storage_connection: Optional xwstorage connection for remote storage (GCS, etc.)
            connection_cache_path: Optional path to JSON file for persisting connection IDs.
                When set, the same connection id is reused after crash/restart (no conflicting connections).
            proxy_url: Optional HTTP(S) or SOCKS proxy URL for Telegram API (e.g. http://host:port or socks5://user:pass@host:port).
                If not set, PTB uses ALL_PROXY / HTTPS_PROXY / HTTP_PROXY env vars. Use this if you get httpx.ConnectError when sending replies.
        """
        if not api_token:
            raise XWChatProviderError("API token is required")
        super().__init__(connection_cache_path=connection_cache_path)
        self._proxy_url = proxy_url
        self._api_token = api_token
        self._bot_name = bot_name or "telegram"
        self._provider_emoji = "✈️"  # Telegram logo (paper plane)
        self._bot: Bot | None = None
        self._application: Application | None = None
        self._connected = False
        self._auto_save_users = auto_save_users
        self._pid_file: Path | None = None
        self._listening = False
        self._agent_id = agent_id or "default"
        self._enable_message_logging = enable_message_logging
        self._message_log_path: Path | None = None
        self._agent_id_set = False
        self._storage_connection = storage_connection
        self._use_remote_storage = storage_connection is not None
        # Set up base data path
        if data_path:
            base_data_path = Path(data_path)
        else:
            # Default: xwchat/.data/xwchat
            current_file = Path(__file__).resolve()
            # Go up from: xwchat/src/exonware/xwchat/providers/telegram.py
            # To: xwchat/
            xwchat_root = current_file.parent.parent.parent.parent.parent
            base_data_path = xwchat_root / ".data" / "xwchat"
        # Set up storage path
        if storage_path:
            self._storage_path = Path(storage_path)
        else:
            # Default: .data/xwchat/{agent_id}/providers/telegram/users/saved_users.json
            self._storage_path = base_data_path / self._agent_id / "providers" / "telegram" / "users" / "saved_users.json"
        # Set up message log path
        if self._enable_message_logging:
            # .data/xwchat/{agent_id}/providers/telegram/messages_log.csv
            self._message_log_path = base_data_path / self._agent_id / "providers" / "telegram" / "messages_log.csv"
            # Ensure directory exists
            self._message_log_path.parent.mkdir(parents=True, exist_ok=True)
            # Initialize CSV file with headers if it doesn't exist
            if not self._message_log_path.exists():
                self._init_message_log()
        # Set up PID file for process management
        if self._storage_path:
            # PID file: data/xwchat/{agent_id}/providers/telegram/bot.pid
            self._pid_file = self._storage_path.parent.parent / "bot.pid"
        self._connection_id = self.get_connection_id(api_token)
    @property

    def provider_type(self) -> ChatProviderType:
        """Get provider type."""
        return ChatProviderType.TELEGRAM
    @property

    def provider_name(self) -> str:
        """Get provider name."""
        return self._bot_name

    @property
    def capabilities(self) -> frozenset[ChatCapability]:
        """Telegram capabilities per REF_12_IDEA §3.1."""
        return frozenset({
            ChatCapability.IDENTITY_AUTH,
            ChatCapability.RECEIVE_MESSAGES,
            ChatCapability.SEND_MESSAGES,
            ChatCapability.READ_HISTORY,
            ChatCapability.ATTACHMENTS,
            ChatCapability.THREADS,
            ChatCapability.REACTIONS,
            ChatCapability.COMMANDS,
        })

    @property

    def api_token(self) -> str:
        """Get API token."""
        return self._api_token
    @property

    def storage_path(self) -> Path:
        """Get storage path for user data."""
        return self._storage_path

    def set_message_handler_legacy(
        self,
        handler: Callable[[str, str, dict[str, Any]], Any],
    ) -> None:
        """
        Set a message handler with legacy signature (user_id, text, message_data).
        Adapts to the standard MessageContext handler. Prefer set_message_handler(ctx).
        """
        def adapt(ctx: MessageContext) -> str | None:
            result = handler(
                ctx.get("user_id", ""),
                ctx.get("text", ""),
                dict(ctx),
            )
            if isinstance(result, str):
                return result
            return None
        super().set_message_handler(adapt)

    async def connect(self) -> None:
        """Connect to Telegram. Retries up to 3 times on network errors."""
        if self._connected:
            logger.warning(f"{self._log_prefix()}Already connected to Telegram")
            return
        self._bot = Bot(token=self._api_token)
        builder = Application.builder().token(self._api_token)
        if self._proxy_url:
            builder = builder.proxy(self._proxy_url).get_updates_proxy(self._proxy_url)
        self._application = builder.build()
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                bot_info = await self._bot.get_me()
                logger.info(f"{self._log_prefix()}Connected to Telegram as @{bot_info.username}")
                self._connected = True
                return
            except NetworkError as e:
                last_err = e
                if attempt < 2:
                    await asyncio.sleep(2.0 * (attempt + 1))
            except TelegramError as e:
                raise XWChatConnectionError(f"Failed to connect to Telegram: {e}") from e
            except Exception as e:
                raise XWChatConnectionError(f"Unexpected error connecting to Telegram: {e}") from e
        if last_err is not None:
            raise XWChatConnectionError(f"Failed to connect to Telegram: {last_err}") from last_err

    async def disconnect(self) -> None:
        """Disconnect from Telegram."""
        # Stop listening if active
        if self._listening:
            await self._shutdown_listener()
        if not self._connected:
            return
        try:
            # Stop application if running
            if self._application:
                try:
                    await self._application.stop()
                    await self._application.shutdown()
                except Exception as app_error:
                    logger.debug(f"Error stopping application (ignored): {app_error}")
                self._application = None
            if self._bot:
                # Close any active sessions
                try:
                    await self._bot.close()
                except Exception as close_error:
                    # Ignore flood control and other errors during close
                    logger.debug(f"Error during bot close (ignored): {close_error}")
            self._bot = None
            self._connected = False
            logger.info(f"{self._log_prefix()}Disconnected from Telegram")
        except Exception as e:
            # Log but don't raise - disconnection should be best-effort
            logger.warning(f"Error disconnecting from Telegram: {e}")
            # Still mark as disconnected even if close failed
            self._bot = None
            self._application = None
            self._connected = False
        finally:
            # Always remove PID file on disconnect
            self._remove_pid()

    async def is_connected(self) -> bool:
        """Check if provider is connected."""
        return self._connected and self._bot is not None

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Send message to a chat.
        Args:
            chat_id: Telegram chat ID (same as user_id in 1:1)
            text: Message text
            reply_to_message_id: Optional message ID to reply to
            **kwargs: Additional message options (parse_mode, etc.)
        Returns:
            Sent message object
        """
        if not await self.is_connected():
            await self.connect()
        if not self._bot:
            raise XWChatConnectionError("Not connected to Telegram")
        try:
            # Resolve chat_id (support saved user lookup for proactive messaging)
            resolved_id: Any = None
            saved_user = await self.get_saved_user(chat_id)
            if saved_user and saved_user.get("chat_id"):
                resolved_id = int(saved_user["chat_id"]) if str(saved_user["chat_id"]).isdigit() else saved_user["chat_id"]
                logger.debug("Using saved chat_id %s for %s", resolved_id, chat_id)
            if not resolved_id:
                resolved_id = int(chat_id) if chat_id.isdigit() else chat_id
                logger.debug("Using chat_id as-is: %s", resolved_id)
            reply_kw: dict[str, Any] = {}
            if reply_to_message_id:
                reply_kw["reply_to_message_id"] = int(reply_to_message_id)
            message = await self._bot.send_message(
                chat_id=resolved_id,
                text=text,
                **reply_kw,
                **kwargs,
            )
            # Log the message to CSV
            if self._enable_message_logging and message:
                await self._log_message(
                    chat_id=str(chat_id),
                    username=saved_user.get("username") if saved_user else None,
                    first_name=saved_user.get("first_name") if saved_user else None,
                    message_id=str(message.message_id),
                    reply_to_message_id=reply_to_message_id or "",
                    message_type="agent",
                    message=text,
                    datetime=message.date.isoformat() if message.date else datetime.now().isoformat()
                )
            logger.debug(f"Sent message to {chat_id}: {text[:50]}...")
            return message
        except TelegramError as e:
            raise XWChatProviderError(f"Failed to send message: {e}") from e
        except Exception as e:
            raise XWChatProviderError(f"Unexpected error sending message: {e}") from e

    async def receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        """
        Receive messages from Telegram.
        This starts the bot and listens for incoming messages.
        Messages are yielded as they arrive.
        Yields:
            Message dictionaries with keys: user_id, text, message_id, etc.
        """
        if not await self.is_connected():
            await self.connect()
        if not self._application:
            raise XWChatConnectionError("Application not initialized")
        # Queue to store incoming messages
        import asyncio
        message_queue = asyncio.Queue()
        async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Handle incoming messages."""
            if update.message and update.message.text:
                message_data = {
                    "user_id": str(update.message.from_user.id),
                    "username": update.message.from_user.username,
                    "text": update.message.text,
                    "message_id": str(update.message.message_id),
                    "chat_id": str(update.message.chat.id),
                    "date": update.message.date.isoformat() if update.message.date else None,
                }
                await message_queue.put(message_data)
        # Add message handler
        self._application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        # Start the application
        await self._application.initialize()
        await self._application.start()
        await self._application.updater.start_polling()
        logger.info(f"{self._log_prefix()}Started listening for messages...")
        # Yield messages as they arrive
        try:
            while True:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(message_queue.get(), timeout=1.0)
                    yield message
                except asyncio.TimeoutError:
                    # Check if still connected
                    if not self._connected:
                        break
                    continue
        finally:
            # Cleanup
            try:
                await self._application.updater.stop()
                await self._application.stop()
                await self._application.shutdown()
            except Exception:
                pass


    def _check_and_kill_existing_process(self) -> None:
        """Check for existing bot process and kill it if found."""
        if not self._pid_file:
            return
        try:
            if not self._pid_file.exists():
                return
            with open(self._pid_file, 'r') as f:
                old_pid = int(f.read().strip())
            if sys.platform == 'win32':
                # Windows: os.kill(pid, 0) raises WinError 87; use taskkill to kill (or detect missing)
                import subprocess
                result = subprocess.run(
                    ['taskkill', '/F', '/PID', str(old_pid)],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    logger.debug(
                        "Stale PID file (process %s gone or not killable), removing it",
                        old_pid,
                    )
                try:
                    self._pid_file.unlink()
                except OSError:
                    pass
                return
            # Unix: check if process exists with signal 0
            try:
                os.kill(old_pid, 0)
            except ProcessLookupError:
                logger.debug(
                    "Stale PID file found (process %s does not exist), removing it",
                    old_pid,
                )
                try:
                    self._pid_file.unlink()
                except OSError:
                    pass
                return
            logger.warning("Found existing bot process (PID: %s), terminating it...", old_pid)
            try:
                os.kill(old_pid, signal.SIGTERM)
                import time
                time.sleep(2)
                try:
                    os.kill(old_pid, 0)
                    logger.warning("Process %s still running, force killing...", old_pid)
                    os.kill(old_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            except ProcessLookupError:
                pass
            except PermissionError as e:
                logger.warning("Error killing process %s: %s", old_pid, e)
            try:
                self._pid_file.unlink()
            except OSError:
                pass
        except (ValueError, OSError) as e:
            logger.warning("Error checking/killing existing process: %s", e)
            try:
                if self._pid_file.exists():
                    self._pid_file.unlink()
            except OSError:
                pass
        except Exception as e:
            logger.warning("Error checking/killing existing process: %s", e)
        # Try to stop any existing polling by calling getUpdates with offset
        try:
            if self._bot:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._bot.get_updates(offset=-1, limit=1, timeout=1))
                else:
                    loop.run_until_complete(self._bot.get_updates(offset=-1, limit=1, timeout=1))
        except Exception:
            pass

    def _save_pid(self) -> None:
        """Save current process ID to file."""
        if not self._pid_file:
            return
        try:
            self._pid_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._pid_file, 'w') as f:
                f.write(str(os.getpid()))
            logger.debug(f"Saved PID {os.getpid()} to {self._pid_file}")
        except Exception as e:
            logger.warning(f"Error saving PID: {e}")

    def _remove_pid(self) -> None:
        """Remove PID file."""
        if not self._pid_file:
            return
        try:
            if self._pid_file.exists():
                self._pid_file.unlink()
                logger.debug(f"Removed PID file {self._pid_file}")
        except Exception as e:
            logger.warning(f"Error removing PID file: {e}")

    async def start_listening(self) -> None:
        """
        Start listening for incoming messages and auto-respond if handler is set.
        This is a convenience method that starts the bot and handles messages.
        It will automatically terminate any existing bot instances.
        """
        # Check and kill existing process FIRST
        self._check_and_kill_existing_process()
        # Wait a bit for process to fully terminate
        import time
        time.sleep(2)
        if not await self.is_connected():
            await self.connect()
        if not self._application:
            raise XWChatConnectionError("Application not initialized")
        # Stop any existing polling first
        try:
            if self._application.updater:
                try:
                    await self._application.updater.stop()
                except Exception:
                    pass
        except Exception:
            pass
        # Save PID
        self._save_pid()
        self._listening = True
        self._polling_network_error_count = 0
        _POLLING_NETWORK_ERROR_LIMIT = 5  # Stop only after this many consecutive polling errors
        loop = asyncio.get_running_loop()
        old_handler = loop.get_exception_handler()

        def _polling_exception_handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:
            exc = context.get("exception")
            message = context.get("message", "Unknown error")
            if isinstance(exc, NetworkError):
                self._polling_network_error_count += 1
                logger.error(
                    "Telegram polling network error %s/%s (check internet/proxy/firewall): %s",
                    self._polling_network_error_count,
                    _POLLING_NETWORK_ERROR_LIMIT,
                    exc,
                )
                if self._polling_network_error_count >= _POLLING_NETWORK_ERROR_LIMIT:
                    logger.error("Too many consecutive polling errors, stopping bot.")
                    self._listening = False
                # else: let the library retry; do not set _listening = False
            elif exc is not None:
                logger.error("Polling task error: %s", exc, exc_info=True)
                self._listening = False
            else:
                logger.error("Polling task error: %s", message)
                self._listening = False
            if old_handler is not None:
                old_handler(loop, context)

        loop.set_exception_handler(_polling_exception_handler)
        # Set up signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            logger.info(f"{self._log_prefix()}Received signal {sig}, shutting down...")
            self._listening = False
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._shutdown_listener())
            except Exception:
                pass
        if sys.platform != 'win32':
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        bot_username = ""
        bot_id: int | None = None
        if self._bot:
            try:
                me = await self._bot.get_me()
                if me:
                    bot_username = (me.username or "") or ""
                    bot_id = me.id
            except Exception as e:
                logger.debug("%sget_me() failed (group mentions may not work): %s", self._log_prefix(), e)

        def _polling_error_callback(exc: TelegramError) -> None:
            """Custom error callback so we log a short warning for NetworkError instead of full traceback."""
            if isinstance(exc, NetworkError):
                self._polling_network_error_count += 1
                logger.warning(
                    "%sPolling network error %s/%s (check internet/proxy): %s",
                    self._log_prefix(),
                    self._polling_network_error_count,
                    _POLLING_NETWORK_ERROR_LIMIT,
                    exc,
                )
                if self._polling_network_error_count >= _POLLING_NETWORK_ERROR_LIMIT:
                    logger.error("Too many consecutive polling errors, stopping bot.")
                    self._listening = False
            else:
                logger.error("%sPolling error: %s", self._log_prefix(), exc, exc_info=True)
                self._listening = False

        async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Handle incoming messages (same structure as minimal echo: update.message + text)."""
            # Match minimal working example: only proceed if we have message with text
            if not (update.message and getattr(update.message, "text", None)):
                return
            msg = update.message
            text = msg.text or ""
            raw_text = text
            try:
                chat_type = getattr(msg.chat, "type", "")
                is_group = chat_type in ("group", "supergroup")
                is_channel = chat_type == "channel"
                self._polling_network_error_count = 0
                logger.info(
                    "%sIncoming message chat_id=%s chat_type=%s text_len=%s",
                    self._log_prefix(),
                    msg.chat.id,
                    chat_type,
                    len(text),
                )
                chat_id_str = str(msg.chat.id)
                chat_type_str = str(chat_type) if chat_type is not None else ""
                chat_title = getattr(msg.chat, "title", None) or ""
                user_id_str = str(msg.from_user.id) if msg.from_user else ""
                message_id_str = str(msg.message_id)
                reply_to_msg = getattr(msg, "reply_to_message", None)
                reply_to_id = str(reply_to_msg.message_id) if reply_to_msg else ""
                username = (msg.from_user.username or "") if msg.from_user else ""
                # Mention detection: DM always; group = entity + string check
                mentioned = False
                if not is_group:
                    mentioned = True
                else:
                    if getattr(msg, "entities", None):
                        for ent in msg.entities:
                            etype = getattr(ent, "type", None)
                            if etype == MessageEntity.MENTION:
                                seg = raw_text[ent.offset : ent.offset + ent.length] if (ent.offset is not None and ent.length is not None) else ""
                                if seg and seg.lstrip("@").lower() == (bot_username or "").lower():
                                    mentioned = True
                                    break
                            if etype == MessageEntity.TEXT_MENTION and bot_id is not None:
                                u = getattr(ent, "user", None)
                                if u and getattr(u, "id", None) == bot_id:
                                    mentioned = True
                                    break
                    if not mentioned and bot_username and ("@" + bot_username).lower() in raw_text.lower():
                        mentioned = True
                if is_group and not mentioned:
                    return
                # Strip @bot from text so handler gets clean text and we don't echo the mention in replies
                if bot_username and (is_group or is_channel):
                    text = _strip_bot_mention(text.strip(), bot_username)
                else:
                    text = text.strip()
                ctx: MessageContext = {
                    "chat_id": chat_id_str,
                    "user_id": user_id_str,
                    "text": text,
                    "message_id": message_id_str,
                    "username": username,
                    "group": is_group,
                    "channel": False,
                    "mentioned": mentioned,
                    "channel_id": chat_id_str,
                    "group_id": chat_id_str if is_group else "",
                    "chat_type": chat_type_str,
                    "chat_title": str(chat_title) if chat_title else "",
                }
                if reply_to_id:
                    ctx["reply_to_message_id"] = reply_to_id
                    ctx["is_reply"] = True
                ctx["help_format"] = "telegram_html"
                message_data = {
                    "user_id": user_id_str,
                    "username": msg.from_user.username if msg.from_user else None,
                    "first_name": msg.from_user.first_name if msg.from_user else None,
                    "text": text,
                    "message_id": message_id_str,
                    "reply_to_message_id": reply_to_id,
                    "chat_id": chat_id_str,
                    "date": msg.date.isoformat() if msg.date else None,
                    "chat_type": chat_type_str,
                    "chat_title": str(chat_title) if chat_title else "",
                    "help_format": "telegram_html",
                }
                if self._enable_message_logging:
                    await self._log_message(
                        chat_id=chat_id_str,
                        username=message_data.get("username"),
                        first_name=message_data.get("first_name"),
                        message_id=message_id_str,
                        reply_to_message_id=reply_to_id,
                        message_type="user",
                        message=text,
                        datetime=message_data.get("date") or datetime.now().isoformat(),
                    )
                if self._auto_save_users:
                    try:
                        await self._save_user_info(user_id_str, message_data)
                    except Exception as e:
                        logger.error("Error auto-saving user info: %s", e, exc_info=True)
                response = self.invoke_message_handler(ctx)
                if asyncio.iscoroutine(response):
                    response = await response
                self.log_message_received(ctx, response is not None)
                response_message = None
                should_reply = bool(response) and (not is_group or mentioned)
                if should_reply:
                    try:
                        resp_text, resp_reply_to, send_kwargs = self._normalize_response(response)
                        if resp_text:
                            if bot_username and (is_group or is_channel):
                                resp_text = _strip_bot_mention(resp_text, bot_username)
                            if resp_text:
                                reply_to_msg_id: int | None = None
                                try:
                                    reply_to_msg_id = int(resp_reply_to or reply_to_id or message_id_str)
                                except (ValueError, TypeError):
                                    pass
                                send_kw = _merge_send_kwargs(send_kwargs)
                                try:
                                    response_message = await msg.reply_text(
                                        resp_text, reply_to_message_id=reply_to_msg_id, **send_kw
                                    )
                                except BadRequest as e:
                                    err = str(e).lower()
                                    if send_kw.get("parse_mode") and (
                                        "parse" in err or "entity" in err or "can't find" in err
                                    ):
                                        logger.warning(
                                            "%sFormatted reply rejected (%s); retrying as plain text.",
                                            self._log_prefix(),
                                            e,
                                        )
                                        plain = _telegram_plain_from_entities(resp_text)
                                        try:
                                            response_message = await msg.reply_text(
                                                plain[:4096],
                                                reply_to_message_id=reply_to_msg_id,
                                                disable_web_page_preview=True,
                                            )
                                        except BadRequest as e2:
                                            logger.error("%sPlain reply also failed: %s", self._log_prefix(), e2)
                                            response_message = None
                                    else:
                                        logger.error("%sBadRequest sending reply: %s", self._log_prefix(), e)
                                        response_message = None
                                except NetworkError as e:
                                    logger.warning(
                                        "%sCould not send reply (network): %s — check internet, firewall, or set proxy (HTTPS_PROXY / proxy_url).",
                                        self._log_prefix(),
                                        e,
                                    )
                                    response_message = None
                    except Exception as e:
                        logger.error("Error sending reply: %s", e)
                elif not is_group and not self._message_handler:
                    response_message = await msg.reply_text(
                        f"You said: {text}",
                        reply_to_message_id=int(reply_to_id) if reply_to_id else None,
                    )
                if self._enable_message_logging and response_message:
                    await self._log_message(
                        chat_id=chat_id_str,
                        username=None,
                        first_name=None,
                        message_id=str(getattr(response_message, "message_id", "")),
                        reply_to_message_id=message_id_str,
                        message_type="agent",
                        message=getattr(response_message, "text", "") or "",
                        datetime=getattr(response_message, "date", None).isoformat() if getattr(response_message, "date", None) else datetime.now().isoformat(),
                    )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("%sError handling message (chat_id=%s): %s", self._log_prefix(), getattr(msg, "chat", None) and getattr(msg.chat, "id", None), e)

        # TEXT including commands (e.g. /weather, /repeat) so xwbots command handler can process them
        self._application.add_handler(MessageHandler(filters.TEXT, message_handler))
        logger.info(f"{self._log_prefix()}Started listening for messages with auto-response...")
        # Start the application with polling (async version for use within async context)
        try:
            # Initialize and start the application
            await self._application.initialize()
            await self._application.start()
            # Start polling
            await self._application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=["message"],
                error_callback=_polling_error_callback,
            )
            logger.info(f"{self._log_prefix()}Bot is now listening for messages...")
            # Keep running until interrupted
            try:
                # Wait indefinitely (or until cancelled)
                while self._listening:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info(f"{self._log_prefix()}Received cancellation, stopping...")
            except KeyboardInterrupt:
                logger.info(f"{self._log_prefix()}Received keyboard interrupt, stopping...")
                self._listening = False
        except (KeyboardInterrupt, SystemExit):
            logger.info(f"{self._log_prefix()}Stopping message listener...")
        finally:
            try:
                loop.set_exception_handler(old_handler)
            except Exception:
                pass
            # Cleanup
            await self._shutdown_listener()

    async def _shutdown_listener(self) -> None:
        """Shutdown the listener gracefully."""
        self._listening = False
        try:
            if self._application:
                # Suppress noisy traceback from ptb's get_updates cleanup (network error during shutdown)
                _telegram_loggers = [
                    logging.getLogger("telegram"),
                    logging.getLogger("telegram.ext"),
                    logging.getLogger("telegram.ext._updater"),
                ]
                _old_levels = [lg.level for lg in _telegram_loggers]
                for lg in _telegram_loggers:
                    lg.setLevel(logging.CRITICAL)
                try:
                    try:
                        await self._application.updater.stop()
                    except Exception:
                        pass
                    try:
                        await self._application.stop()
                    except Exception:
                        pass
                    try:
                        await self._application.shutdown()
                    except Exception:
                        pass
                finally:
                    for lg, level in zip(_telegram_loggers, _old_levels):
                        lg.setLevel(level)
        except Exception as e:
            logger.debug(f"Error during cleanup: {e}")
        finally:
            # Remove PID file
            self._remove_pid()
            logger.info(f"{self._log_prefix()}Listener shutdown complete")

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """
        Get user information.
        Args:
            user_id: Telegram user ID
        Returns:
            User information dictionary
        """
        if not await self.is_connected():
            await self.connect()
        if not self._bot:
            raise XWChatConnectionError("Not connected to Telegram")
        try:
            chat_id = int(user_id) if user_id.isdigit() else user_id
            chat = await self._bot.get_chat(chat_id=chat_id)
            return {
                "id": str(chat.id),
                "username": chat.username,
                "first_name": chat.first_name,
                "last_name": chat.last_name,
                "type": chat.type.value if hasattr(chat.type, 'value') else str(chat.type),
            }
        except TelegramError as e:
            raise XWChatProviderError(f"Failed to get user info: {e}") from e
        except Exception as e:
            raise XWChatProviderError(f"Unexpected error getting user info: {e}") from e

    async def user_exists(self, username: str) -> bool:
        """Check if a Telegram username exists (implements AChatProvider)."""
        return await asyncio.to_thread(user_exists, username)

    async def get_user_id(self, username: str) -> str | None:
        """
        Get user ID by username.
        Tries multiple methods:
        1. Web scraping to extract ID from HTML (if available)
        2. Bot API (requires user interaction)
        Args:
            username: Telegram username (with or without @)
        Returns:
            User ID as string, or None if user not found
        """
        # Remove @ if present
        username = username.lstrip('@').strip()
        if not username:
            return None
        # First verify user exists via web scraping
        if not user_exists(username):
            return None
        # Try to extract user ID from HTML (web scraping)
        try:
            url = f"https://t.me/{username}"
            # Get HTML content
            import httpx
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                html_content = response.text
            # Try to extract user ID from HTML using various patterns
            import re
            from collections import Counter
            # Pattern 1: Look for data-user-id attribute
            pattern1 = r'data-user-id=["\'](\d+)["\']'
            match = re.search(pattern1, html_content)
            if match:
                user_id = match.group(1)
                logger.debug(f"Found user ID via data-user-id attribute: {user_id}")
                return user_id
            # Pattern 2: Look for user IDs in JSON-like structures
            pattern2 = r'"user_id":\s*(\d+)'
            match = re.search(pattern2, html_content)
            if match:
                user_id = match.group(1)
                logger.debug(f"Found user ID via JSON pattern: {user_id}")
                return user_id
            # Pattern 3: Find most common 8+ digit number (likely user ID)
            # This is less reliable but sometimes works
            all_ids = re.findall(r'\b(\d{8,})\b', html_content)
            if all_ids:
                id_counts = Counter(all_ids)
                # Get the most common ID that appears multiple times
                most_common = id_counts.most_common(1)[0]
                if most_common[1] >= 2:  # Appears at least twice
                    user_id = most_common[0]
                    logger.debug(f"Found user ID via frequency analysis: {user_id}")
                    return user_id
        except Exception as e:
            logger.debug(f"Could not extract user ID from HTML: {e}")
        # Fallback: Try Bot API (requires user interaction)
        try:
            if not await self.is_connected():
                await self.connect()
            if not self._bot:
                raise XWChatConnectionError("Not connected to Telegram")
            # Get chat by username
            chat = await self._bot.get_chat(chat_id=f"@{username}")
            if chat and chat.id:
                return str(chat.id)
            return None
        except TelegramError as e:
            logger.debug(f"User not found or not accessible via Bot API: {e}")
            # User exists on web but bot can't access - might need interaction first
            return None
        except Exception as e:
            logger.warning(f"Error getting user ID: {e}")
            return None

    async def _save_user_info(self, user_id: str, message_data: dict[str, Any]) -> None:
        """
        Save user information to storage.
        Args:
            user_id: Telegram user ID
            message_data: Message data containing user information
        """
        try:
            # Load existing users
            users = await self._load_users()
            # Get or create user entry
            if user_id not in users:
                users[user_id] = {}
            # Update user info
            user_info = users[user_id]
            # CRITICAL: Save chat_id if available (needed for proactive messaging)
            chat_id = message_data.get("chat_id")
            if chat_id:
                user_info["chat_id"] = str(chat_id)  # Ensure it's a string
                logger.info(f"Saved chat_id {chat_id} for user {user_id}")
            elif not user_info.get("chat_id"):
                logger.warning(f"No chat_id in message_data for user {user_id}, message_data keys: {list(message_data.keys())}")
            user_info.update({
                "id": user_id,
                "username": message_data.get("username"),
                "last_message": message_data.get("text"),
                "last_message_date": message_data.get("date"),
                "last_seen": message_data.get("date"),
                "message_count": user_info.get("message_count", 0) + 1,
            })
            # Try to get full user info from Telegram API
            try:
                if await self.is_connected() and self._bot:
                    chat = await self._bot.get_chat(chat_id=int(user_id))
                    user_info.update({
                        "first_name": chat.first_name,
                        "last_name": chat.last_name,
                        "username": chat.username or user_info.get("username"),
                    })
            except Exception:
                pass  # Ignore if we can't get full info
            # Save to storage
            await self._save_users(users)
            logger.info(f"Saved user info for {user_id} (chat_id: {user_info.get('chat_id', 'NOT SET')}) to {self._storage_path}")
        except Exception as e:
            logger.warning(f"Error saving user info: {e}")

    async def _load_users(self) -> dict[str, dict[str, Any]]:
        """Load users from storage."""
        if self._use_remote_storage and self._storage_connection:
            # Use remote storage (GCS, etc.)
            try:
                remote_path = f"{self._agent_id}/providers/telegram/users/saved_users.json"
                if await self._storage_connection.exists(remote_path):
                    users = await self._storage_connection.load(remote_path)
                    logger.debug(f"Loaded users from remote storage: {remote_path}")
                    return users if isinstance(users, dict) else {}
                else:
                    logger.debug(f"Remote storage path does not exist: {remote_path}")
                    return {}
            except Exception as e:
                logger.warning(f"Error loading users from remote storage: {e}")
                # Fallback to local storage
                return await self._load_users_local()
        else:
            # Use local storage
            return await self._load_users_local()

    async def _load_users_local(self) -> dict[str, dict[str, Any]]:
        """Load users from local storage."""
        if not self._storage_path or not self._storage_path.exists():
            return {}
        try:
            return JsonSerializer().load_file(self._storage_path)
        except Exception as e:
            logger.warning(f"Error loading users: {e}")
            return {}

    async def _save_users(self, users: dict[str, dict[str, Any]]) -> None:
        """Save users to storage."""
        if self._use_remote_storage and self._storage_connection:
            # Use remote storage (GCS, etc.)
            try:
                # Use agent_id-based path in remote storage
                remote_path = f"{self._agent_id}/providers/telegram/users/saved_users.json"
                await self._storage_connection.save(users, remote_path)
                logger.debug(f"Saved users to remote storage: {remote_path}")
            except Exception as e:
                logger.warning(f"Error saving users to remote storage: {e}")
                # Fallback to local storage
                await self._save_users_local(users)
        else:
            # Use local storage
            await self._save_users_local(users)

    async def _save_users_local(self, users: dict[str, dict[str, Any]]) -> None:
        """Save users to local storage."""
        if not self._storage_path:
            return
        try:
            # Ensure directory exists
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            JsonSerializer().save_file(users, self._storage_path, indent=2, ensure_ascii=False)
            logger.debug(f"Saved users to {self._storage_path}")
        except Exception as e:
            logger.warning(f"Error saving users to {self._storage_path}: {e}")

    async def get_saved_user(self, user_id: str) -> dict[str, Any] | None:
        """
        Get saved user information.
        Args:
            user_id: Telegram user ID
        Returns:
            User information dictionary or None if not found
        """
        users = await self._load_users()
        return users.get(user_id)

    async def get_all_saved_users(self) -> dict[str, dict[str, Any]]:
        """
        Get all saved users.
        Returns:
            Dictionary mapping user_id to user info
        """
        return await self._load_users()

    async def save_user_manually(self, user_id: str, user_info: dict[str, Any] | None = None, username: str | None = None) -> None:
        """
        Manually save user information.
        Args:
            user_id: Telegram user ID
            user_info: Optional user info dict. If None, will fetch from Telegram API.
            username: Username to save if user_info is not available
        """
        if user_info is None:
            # Try to get from Telegram API
            try:
                user_info = await self.get_user_info(user_id)
            except Exception as e:
                logger.debug(f"Could not fetch user info from API: {e}")
                user_info = {}
        message_data = {
            "user_id": user_id,
            "username": user_info.get("username") or username,
            "text": "",
            "date": None,
        }
        await self._save_user_info(user_id, message_data)
        logger.info(f"Saved user {user_id} to {self._storage_path}")

    def _init_message_log(self) -> None:
        """Initialize CSV message log file with headers."""
        if not self._message_log_path:
            return
        try:
            with open(self._message_log_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'chat_id', 'username', 'first_name', 'datetime', 
                    'message_id', 'reply_to_message_id', 'message_type', 'message'
                ])
                writer.writeheader()
            logger.debug(f"Initialized message log at {self._message_log_path}")
        except Exception as e:
            logger.warning(f"Error initializing message log: {e}")

    async def _log_message(
        self,
        chat_id: str,
        username: str | None,
        first_name: str | None,
        message_id: str,
        reply_to_message_id: str,
        message_type: str,  # 'user' or 'agent'
        message: str,
        datetime: str
    ) -> None:
        """Log a message to CSV file."""
        if not self._enable_message_logging:
            return
        message_row = {
            'chat_id': chat_id or '',
            'username': username or '',
            'first_name': first_name or '',
            'datetime': datetime,
            'message_id': message_id or '',
            'reply_to_message_id': reply_to_message_id or '',
            'message_type': message_type,
            'message': message
        }
        if self._use_remote_storage and self._storage_connection:
            # Use remote storage for CSV logging
            try:
                remote_path = f"{self._agent_id}/providers/telegram/messages_log.csv"
                # Load existing CSV if exists, append, and save
                if await self._storage_connection.exists(remote_path):
                    existing_csv = await self._storage_connection.load(remote_path)
                    # Parse CSV and append
                    import io
                    import csv as csv_module
                    rows = list(csv_module.DictReader(io.StringIO(existing_csv)))
                    rows.append(message_row)
                    # Re-serialize
                    output = io.StringIO()
                    writer = csv_module.DictWriter(output, fieldnames=[
                        'chat_id', 'username', 'first_name', 'datetime', 
                        'message_id', 'reply_to_message_id', 'message_type', 'message'
                    ])
                    writer.writeheader()
                    writer.writerows(rows)
                    await self._storage_connection.save(output.getvalue(), remote_path)
                else:
                    # Create new CSV with header
                    import io
                    import csv as csv_module
                    output = io.StringIO()
                    writer = csv_module.DictWriter(output, fieldnames=[
                        'chat_id', 'username', 'first_name', 'datetime', 
                        'message_id', 'reply_to_message_id', 'message_type', 'message'
                    ])
                    writer.writeheader()
                    writer.writerow(message_row)
                    await self._storage_connection.save(output.getvalue(), remote_path)
                logger.debug(f"Logged {message_type} message to remote storage: {remote_path}")
            except Exception as e:
                logger.warning(f"Error logging message to remote storage: {e}")
                # Fallback to local storage
                await self._log_message_local(message_row)
        else:
            # Use local storage
            await self._log_message_local(message_row)

    async def _log_message_local(self, message_row: dict[str, Any]) -> None:
        """Log a message to local CSV file."""
        if not self._message_log_path:
            return
        try:
            # Check if file exists, if not initialize it
            if not self._message_log_path.exists():
                self._init_message_log()
            # Append message to CSV
            with open(self._message_log_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'chat_id', 'username', 'first_name', 'datetime', 
                    'message_id', 'reply_to_message_id', 'message_type', 'message'
                ])
                writer.writerow(message_row)
            logger.debug(f"Logged {message_row.get('message_type')} message to {self._message_log_path}")
        except Exception as e:
            logger.warning(f"Error logging message to CSV: {e}")


# Backwards-compatible alias
Telegram = TelegramChatProvider
