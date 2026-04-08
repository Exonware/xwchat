from collections.abc import AsyncIterator, Callable
#!/usr/bin/env python3
"""
#exonware/xwchat/src/exonware/xwchat/providers/telegram.py
Telegram chat provider implementation.
Company: eXonware.com
Author: eXonware Backend Team
Email: connect@exonware.com
Version: 0.0.1.0
Generation Date: 07-Jan-2025
"""

from typing import Any
import asyncio
from exonware.xwsystem.io.serialization import JsonSerializer
import os
import signal
import sys
import csv
from datetime import datetime
from pathlib import Path
from exonware.xwsystem import get_logger
from ..base import AChatProvider
from ..defs import ChatProviderType
from ..errors import XWChatConnectionError, XWChatProviderError
logger = get_logger(__name__)
# Prevent BeautifulSoup from trying to import lxml (which has Python 2 syntax issues)
# Block lxml import before BeautifulSoup tries to import it
import sys
if 'lxml' not in sys.modules:
    # Create a dummy module to prevent lxml from being imported
    class DummyModule:
        pass
    sys.modules['lxml'] = DummyModule()
    sys.modules['lxml.etree'] = DummyModule()
# Standard imports - NO try/except!
# These should be declared as dependencies in pyproject.toml
from bs4 import BeautifulSoup
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError


def user_exists(username: str) -> bool:
    """
    Check if a Telegram username exists by web scraping.
    This is the single function for checking Telegram username existence.
    It uses web scraping to check if a user exists, which works even if the bot hasn't
    interacted with the user.
    This function reuses the text extraction pattern from extract_webpage_text (xwsystem.utils.web)
    but uses httpx for HTTP requests to support timeout.
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
    # Remove @ if present
    username = username.lstrip('@').strip()
    if not username:
        return False
    try:
        url = f"https://t.me/{username}"
        # Use httpx for HTTP requests with timeout (better than urlopen in extract_webpage_text)
        import httpx
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            if response.status_code != 200:
                return False
            html_content = response.text
        # Parse HTML using the same pattern as extract_webpage_text (xwsystem.utils.web)
        # This reuses the text extraction logic for consistency across the codebase
        soup = BeautifulSoup(html_content, features="html.parser")
        # Remove script and style elements (same as extract_webpage_text)
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text()
        # Apply the same text normalization as extract_webpage_text
        # Break into lines and remove leading/trailing space
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        # Check for "Send Message" which indicates user exists
        if "Send Message" in text:
            return True
        # Check for "Download\nIf" or "Download" followed by "If" which indicates user doesn't exist
        # The original implementation in xwapi_agent.py looked for 'Download\nIf' as a single string
        if "Download\nIf" in text:
            return False
        # Also check for "Download" and "If you have" appearing close together
        if "Download" in text and "If you have" in text:
            download_pos = text.find("Download")
            if_pos = text.find("If you have")
            if download_pos > 0 and if_pos > 0 and abs(download_pos - if_pos) < 100:
                return False
        # If we have the username in the page, user likely exists
        return username.lower() in text.lower()
    except Exception as e:
        logger.warning(f"Error checking if Telegram username exists via web: {e}")
        return False


class Telegram(AChatProvider):
    """Telegram chat provider implementation."""

    def __init__(self, api_token: str, bot_name: str | None = None, storage_path: str | None = None, auto_save_users: bool = True, agent_id: str | None = None, data_path: str | None = None, enable_message_logging: bool = True, storage_connection: Any | None = None):
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
        """
        if not api_token:
            raise XWChatProviderError("API token is required")
        self._api_token = api_token
        self._bot_name = bot_name or "telegram"
        self._bot: Bot | None = None
        self._application: Application | None = None
        self._connected = False
        self._message_handler: Callable[[str, str, dict[str, Any]], Any] | None = None
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
            # Default: xwchat/data/xwchat
            current_file = Path(__file__).resolve()
            # Go up from: xwchat/src/exonware/xwchat/providers/telegram.py
            # To: xwchat/
            xwchat_root = current_file.parent.parent.parent.parent.parent
            base_data_path = xwchat_root / "data" / "xwchat"
        # Set up storage path
        if storage_path:
            self._storage_path = Path(storage_path)
        else:
            # Default: data/xwchat/{agent_id}/providers/telegram/users/saved_users.json
            self._storage_path = base_data_path / self._agent_id / "providers" / "telegram" / "users" / "saved_users.json"
        # Set up message log path
        if self._enable_message_logging:
            # data/xwchat/{agent_id}/providers/telegram/messages_log.csv
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
    @property

    def provider_type(self) -> ChatProviderType:
        """Get provider type."""
        return ChatProviderType.TELEGRAM
    @property

    def provider_name(self) -> str:
        """Get provider name."""
        return self._bot_name
    @property

    def api_token(self) -> str:
        """Get API token."""
        return self._api_token
    @property

    def storage_path(self) -> Path:
        """Get storage path for user data."""
        return self._storage_path

    async def connect(self) -> None:
        """Connect to Telegram."""
        if self._connected:
            logger.warning("Already connected to Telegram")
            return
        try:
            # Create bot instance
            self._bot = Bot(token=self._api_token)
            # Create application for message handling
            self._application = Application.builder().token(self._api_token).build()
            # Test connection by getting bot info
            bot_info = await self._bot.get_me()
            logger.info(f"Connected to Telegram as @{bot_info.username}")
            self._connected = True
        except TelegramError as e:
            raise XWChatConnectionError(f"Failed to connect to Telegram: {e}") from e
        except Exception as e:
            raise XWChatConnectionError(f"Unexpected error connecting to Telegram: {e}") from e

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
            logger.info("Disconnected from Telegram")
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

    async def send_message(self, user_id: str, text: str, **kwargs) -> Any:
        """
        Send message to user.
        Args:
            user_id: Telegram user/chat ID
            text: Message text
            **kwargs: Additional message options (parse_mode, reply_to_message_id, etc.)
        Returns:
            Sent message object
        """
        if not await self.is_connected():
            await self.connect()
        if not self._bot:
            raise XWChatConnectionError("Not connected to Telegram")
        try:
            # Try to get chat_id from saved users first (more reliable)
            chat_id = None
            saved_user = await self.get_saved_user(user_id)
            if saved_user and saved_user.get("chat_id"):
                chat_id = int(saved_user.get("chat_id")) if str(saved_user.get("chat_id")).isdigit() else saved_user.get("chat_id")
                logger.debug(f"Using saved chat_id {chat_id} for user {user_id}")
            # Fallback to user_id if chat_id not found
            if not chat_id:
                chat_id = int(user_id) if user_id.isdigit() else user_id
                logger.debug(f"Using user_id as chat_id: {chat_id}")
            # Send the message
            message = await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                **kwargs
            )
            # Log the message to CSV
            if self._enable_message_logging and message:
                await self._log_message(
                    chat_id=str(chat_id),
                    username=saved_user.get("username") if saved_user else None,
                    first_name=saved_user.get("first_name") if saved_user else None,
                    message_id=str(message.message_id),
                    reply_to_message_id=str(kwargs.get("reply_to_message_id", "")) if kwargs.get("reply_to_message_id") else "",
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
        logger.info("Started listening for messages...")
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

    def set_message_handler(self, handler: Callable[[str, str, dict[str, Any]], Any]) -> None:
        """
        Set a custom message handler function.
        The handler will be called with (user_id: str, text: str, message_data: dict) 
        when a message is received.
        Args:
            handler: Function that takes (user_id, text, message_data) and optionally returns a response
        """
        self._message_handler = handler

    def _check_and_kill_existing_process(self) -> None:
        """Check for existing bot process and kill it if found."""
        if not self._pid_file:
            return
        try:
            if self._pid_file.exists():
                with open(self._pid_file, 'r') as f:
                    old_pid = int(f.read().strip())
                # Check if process is still running
                try:
                    os.kill(old_pid, 0)  # Signal 0 just checks if process exists
                    logger.warning(f"Found existing bot process (PID: {old_pid}), terminating it...")
                    try:
                        # Try graceful termination first
                        if sys.platform == 'win32':
                            # Windows doesn't have SIGTERM, use taskkill
                            import subprocess
                            subprocess.run(['taskkill', '/F', '/PID', str(old_pid)], 
                                         capture_output=True, timeout=5)
                        else:
                            os.kill(old_pid, signal.SIGTERM)
                            import time
                            time.sleep(2)
                            # Check if still running
                            try:
                                os.kill(old_pid, 0)
                                # Force kill if still running
                                logger.warning(f"Process {old_pid} still running, force killing...")
                                if sys.platform == 'win32':
                                    subprocess.run(['taskkill', '/F', '/PID', str(old_pid)], 
                                                 capture_output=True, timeout=5)
                                else:
                                    os.kill(old_pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass  # Process already terminated
                    except ProcessLookupError:
                        pass  # Process already terminated
                    except (PermissionError, subprocess.TimeoutExpired) as e:
                        logger.warning(f"Error killing process {old_pid}: {e}, may need to kill manually")
                except ProcessLookupError:
                    # Process doesn't exist, just remove stale PID file
                    logger.debug(f"Stale PID file found (process {old_pid} doesn't exist), removing it")
                    self._pid_file.unlink()
        except Exception as e:
            logger.warning(f"Error checking/killing existing process: {e}")
        # Also try to stop any existing polling by calling getUpdates with offset
        # This will clear any pending updates and stop other instances
        try:
            if self._bot:
                # This will cause any other polling instance to fail and stop
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._bot.get_updates(offset=-1, limit=1, timeout=1))
                else:
                    loop.run_until_complete(self._bot.get_updates(offset=-1, limit=1, timeout=1))
        except Exception:
            pass  # Ignore errors here

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
        # Set up signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down...")
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
        async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Handle incoming messages and auto-respond."""
            if update.message and update.message.text:
                user_id = str(update.message.from_user.id)
                text = update.message.text
                reply_to_message_id = str(update.message.reply_to_message.message_id) if update.message.reply_to_message else ""
                message_data = {
                    "user_id": user_id,
                    "username": update.message.from_user.username,
                    "first_name": update.message.from_user.first_name,
                    "text": text,
                    "message_id": str(update.message.message_id),
                    "reply_to_message_id": reply_to_message_id,
                    "chat_id": str(update.message.chat.id),
                    "date": update.message.date.isoformat() if update.message.date else None,
                }
                # Log incoming message to CSV
                if self._enable_message_logging:
                    await self._log_message(
                        chat_id=message_data.get("chat_id"),
                        username=message_data.get("username"),
                        first_name=message_data.get("first_name"),
                        message_id=message_data.get("message_id"),
                        reply_to_message_id=reply_to_message_id,
                        message_type="user",
                        message=text,
                        datetime=message_data.get("date") or datetime.now().isoformat()
                    )
                # Auto-save user info if enabled
                if self._auto_save_users:
                    try:
                        logger.info(f"Auto-saving user info for {user_id}, chat_id: {message_data.get('chat_id')}")
                        await self._save_user_info(user_id, message_data)
                        logger.info(f"Successfully saved user info for {user_id}")
                    except Exception as e:
                        logger.error(f"Error auto-saving user info: {e}", exc_info=True)
                # Call custom handler if set
                response_message = None
                if self._message_handler:
                    try:
                        response = self._message_handler(user_id, text, message_data)
                        if response:
                            # If handler returns a string, send it as response
                            if isinstance(response, str):
                                response_message = await update.message.reply_text(
                                    response, 
                                    reply_to_message_id=int(reply_to_message_id) if reply_to_message_id else None
                                )
                            # If handler is async, await it
                            elif asyncio.iscoroutine(response):
                                result = await response
                                if result and isinstance(result, str):
                                    response_message = await update.message.reply_text(
                                        result,
                                        reply_to_message_id=int(reply_to_message_id) if reply_to_message_id else None
                                    )
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")
                else:
                    # Default: echo the message
                    response_message = await update.message.reply_text(
                        f"You said: {text}",
                        reply_to_message_id=int(reply_to_message_id) if reply_to_message_id else None
                    )
                # Log outgoing response message to CSV
                if self._enable_message_logging and response_message:
                    await self._log_message(
                        chat_id=message_data.get("chat_id"),
                        username=None,  # Bot doesn't have username in this context
                        first_name=None,
                        message_id=str(response_message.message_id),
                        reply_to_message_id=str(update.message.message_id),
                        message_type="agent",
                        message=response_message.text or "",
                        datetime=response_message.date.isoformat() if response_message.date else datetime.now().isoformat()
                    )
        # Add message handler
        self._application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        logger.info("Started listening for messages with auto-response...")
        # Start the application with polling (async version for use within async context)
        try:
            # Initialize and start the application
            await self._application.initialize()
            await self._application.start()
            # Start polling
            await self._application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=None
            )
            logger.info("Bot is now listening for messages...")
            # Keep running until interrupted
            try:
                # Wait indefinitely (or until cancelled)
                while self._listening:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info("Received cancellation, stopping...")
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, stopping...")
                self._listening = False
        except (KeyboardInterrupt, SystemExit):
            logger.info("Stopping message listener...")
        finally:
            # Cleanup
            await self._shutdown_listener()

    async def _shutdown_listener(self) -> None:
        """Shutdown the listener gracefully."""
        self._listening = False
        try:
            if self._application:
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
        except Exception as e:
            logger.debug(f"Error during cleanup: {e}")
        finally:
            # Remove PID file
            self._remove_pid()
            logger.info("Listener shutdown complete")

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
            username: Optional username to save if user_info is not available
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
