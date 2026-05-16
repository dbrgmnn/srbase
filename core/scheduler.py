import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import aiohttp

logger = logging.getLogger(__name__)

async def send_tg_push(token, chat_id, text):
    """Send a simple text message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
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

async def scheduler_loop(app):
    """Background task to notify users at their scheduled time."""
    token = os.getenv("TG_TOKEN")
    mapping_str = os.getenv("TG_MAPPING", "")
    
    if not token or not mapping_str:
        logger.warning("Scheduler disabled: TG_TOKEN or TG_MAPPING missing")
        return

    try:
        user_map = {int(p.split(':')[0]): p.split(':')[1] for p in mapping_str.split(',') if ':' in p}
    except Exception as e:
        logger.error("Invalid TG_MAPPING format: %s", e)
        return

    tz_name = os.getenv("APP_TIMEZONE", "UTC")
    last_sent = {} # {f"{user_id}_{lang}": "YYYY-MM-DD-HH"}
    last_backup_day = None

    lang_meta = {
        "de": {"flag": "🇩🇪", "name": "German"},
        "en": {"flag": "🇬🇧", "name": "English"}
    }

    while True:
        try:
            now = datetime.now(timezone.utc)
            
            # 1. Sleep until the next 30-minute mark (00 or 30)
            if now.minute < 30:
                next_check = now.replace(minute=30, second=0, microsecond=0)
            else:
                next_check = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            
            sleep_seconds = (next_check - now).total_seconds()
            await asyncio.sleep(max(sleep_seconds, 1))

            # 2. Wake up and check all users
            now = datetime.now(ZoneInfo(tz_name))
            
            # --- Daily DB Backup at 12:00 ---
            if now.hour == 12 and last_backup_day != now.date():
                backup_path = f"backup_{now.strftime('%Y%m%d')}.db"
                try:
                    admin_chat_id = list(user_map.values())[1] if len(user_map) >= 2 else list(user_map.values())[0]

                    # Create hot backup
                    await app['db'].execute(f"VACUUM INTO '{backup_path}'")

                    # Send document
                    url = f"https://api.telegram.org/bot{token}/sendDocument"
                    data = aiohttp.FormData()
                    data.add_field('chat_id', str(admin_chat_id))
                    with open(backup_path, 'rb') as f:
                        data.add_field('document', f, filename=backup_path)
                        connector = aiohttp.TCPConnector(ssl=False)
                        async with aiohttp.ClientSession(connector=connector) as session:
                            async with session.post(url, data=data) as resp:
                                if resp.status == 200:
                                    logger.info("Daily backup sent to admin")
                                    last_backup_day = now.date()
                                else:
                                    logger.error("Backup send failed: %s", await resp.text())
                except Exception as be:
                    logger.error("Backup process error: %s", be)
                finally:
                    if os.path.exists(backup_path):
                        os.remove(backup_path)

            current_minutes = now.hour * 60 + now.minute

            hour_key = now.strftime("%Y-%m-%d-%H")

            for user_id, chat_id in user_map.items():
                user_languages = await app['user_repo'].get_all_user_languages(user_id)
                
                for lang in user_languages:
                    settings = await app['user_repo'].get_settings(user_id, lang)
                    target_time = settings.get("notification_time", -1)
                    
                    # Off or not time yet
                    if target_time == -1 or current_minutes < target_time:
                        continue
                        
                    sent_key = f"{user_id}_{lang}"
                    if last_sent.get(sent_key) == hour_key:
                        continue

                    stats = await app['word_repo'].get_full_stats(user_id, lang, daily_limit=settings.get("daily_limit", 20))
                    due = stats.get("due", 0) or 0
                    threshold = settings.get("daily_limit", 20)
                    
                    # Trigger only if reviews reach the daily limit threshold
                    if due >= threshold:
                        new_in_session = (stats.get("session_total", 0) or 0) - due
                        meta = lang_meta.get(lang, {"flag": "🌐", "name": lang.upper()})
                        
                        msg = f"🔔 {meta['name']}: {due} review, {new_in_session} new"
                        
                        logger.info("Notification sent: ID %d [%s] (due: %d)", user_id, lang, due)
                        await send_tg_push(token, chat_id, msg)
                        last_sent[sent_key] = hour_key

        except Exception as e:
            logger.error("Error in scheduler loop: %s", e)
            await asyncio.sleep(60)
