import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
import aiohttp
from core import config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Service to handle Telegram notifications."""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"

    async def send_message(self, chat_id: str | int, text: str):
        """Send a simple text message via Telegram Bot API."""
        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        logger.info("TG notification sent successfully")
                    else:
                        logger.error("TG error: %s", await resp.text())
        except Exception as e:
            logger.error("Failed to send TG notification: %s", e)

    async def send_document(self, chat_id: str | int, file_path: str, filename: str):
        """Send a document via Telegram Bot API."""
        url = f"{self.base_url}/sendDocument"
        data = aiohttp.FormData()
        data.add_field('chat_id', str(chat_id))
        try:
            with open(file_path, 'rb') as f:
                data.add_field('document', f, filename=filename)
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.post(url, data=data) as resp:
                        if resp.status == 200:
                            logger.info("TG document sent successfully")
                            return True
                        else:
                            logger.error("TG document error: %s", await resp.text())
                            return False
        except Exception as e:
            logger.error("Failed to send TG document: %s", e)
            return False

class Scheduler:
    """Background task manager for notifications and maintenance."""
    
    def __init__(self, app):
        self.app = app
        self.token = config.TG_TOKEN
        self.tz = config.APP_TZ
        self.admin_chat_id = config.TG_ADMIN
        self.notifier = TelegramNotifier(self.token) if self.token else None
        
        self.last_sent = {}  # {f"{user_id}_{lang}": "YYYY-MM-DD-HH"}
        self.last_backup_day = None

    async def run(self):
        """Main loop for the scheduler."""
        if not self.notifier:
            logger.warning("Scheduler disabled: TG_TOKEN missing")
            return

        logger.info("Scheduler started")
        while True:
            try:
                await self._wait_until_next_tick()
                await self._tick()
            except Exception as e:
                logger.error("Error in scheduler loop: %s", e)
                await asyncio.sleep(60)

    @staticmethod
    async def _wait_until_next_tick():
        """Sleep until the next 30-minute mark (00 or 30)."""
        now = datetime.now(timezone.utc)
        if now.minute < 30:
            next_check = now.replace(minute=30, second=0, microsecond=0)
        else:
            next_check = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

        sleep_seconds = (next_check - now).total_seconds()
        await asyncio.sleep(max(sleep_seconds, 1))

    async def _tick(self):
        """Run periodic tasks."""
        if not self.notifier:
            return

        now = datetime.now(self.tz)
        
        await self._handle_backups(now)
        await self._handle_notifications(now)

    async def _handle_backups(self, now: datetime):
        """Daily DB Backup at 12:00."""
        if not self.notifier:
            return

        if now.hour == 12 and self.last_backup_day != now.date():
            if not self.admin_chat_id:
                logger.warning("No TG_ADMIN configured for database backups")
                return

            backup_path = f"backup_{now.strftime('%Y%m%d')}.db"
            try:
                # Create hot backup
                await self.app['db'].execute(f"VACUUM INTO '{backup_path}'")

                # Send document
                success = await self.notifier.send_document(self.admin_chat_id, backup_path, backup_path)
                if success:
                    logger.info("Daily backup sent to admin")
                    self.last_backup_day = now.date()
            except Exception as e:
                logger.error("Backup process error: %s", e)
            finally:
                if os.path.exists(backup_path):
                    os.remove(backup_path)

    async def _handle_notifications(self, now: datetime):
        """Periodic user notifications."""
        if not self.notifier:
            return

        current_minutes = now.hour * 60 + now.minute
        hour_key = now.strftime("%Y-%m-%d-%H")

        # Get users from database
        db_users = await self.app['user_repo'].get_users_with_telegram()

        for user in db_users:
            user_id = user["id"]
            chat_id = user["telegram_chat_id"]
            user_languages = await self.app['user_repo'].get_all_user_languages(user_id)
            
            for lang in user_languages:
                settings = await self.app['user_repo'].get_settings(user_id, lang)
                target_time = settings.get("notification_time", -1)
                
                # Off or not time yet
                if target_time == -1 or current_minutes < target_time:
                    continue
                    
                sent_key = f"{user_id}_{lang}"
                if self.last_sent.get(sent_key) == hour_key:
                    continue

                stats = await self.app['word_repo'].get_full_stats(user_id, lang, daily_limit=settings.get("daily_limit", 20))
                due = stats.get("due", 0) or 0
                threshold = settings.get("notification_threshold", 1)
                text_lang = lang.upper()
                
                # Trigger only if reviews reach the notification threshold
                if due >= threshold:
                    new_in_session = (stats.get("session_total", 0) or 0) - due
                    
                    msg = f"🔔 {text_lang}: {due} review, {new_in_session} new"
                    
                    logger.info("Notification sent: ID %d [%s] (due: %d)", user_id, lang, due)
                    await self.notifier.send_message(chat_id, msg)
                    self.last_sent[sent_key] = hour_key
