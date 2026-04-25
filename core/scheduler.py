import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
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

    last_sent = {} # {f"{user_id}_{lang}": "YYYY-MM-DD-HH"}
    logger.info("Scheduler initialized for users: %s", list(user_map.keys()))

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
            
            logger.info("Scheduler sleeping until (UTC): %s", next_check)
            await asyncio.sleep(max(sleep_seconds, 1))

            # 2. Wake up and check all users
            now = datetime.now(timezone.utc)
            current_hour_in_minutes = now.hour * 60
            today_key = now.strftime("%Y-%m-%d-%H")

            for user_id, chat_id in user_map.items():
                user_languages = await app['user_repo'].get_all_user_languages(user_id)
                
                for lang in user_languages:
                    settings = await app['user_repo'].get_settings(user_id, lang)
                    target_time = settings.get("notification_time", -1)
                    
                    sent_key = f"{user_id}_{lang}"
                    
                    # Check if matches target hour and not sent yet
                    if target_time != -1 and target_time == current_hour_in_minutes and last_sent.get(sent_key) != today_key:
                        stats = await app['word_repo'].get_full_stats(user_id, lang, daily_limit=settings.get("daily_limit", 20))
                        
                        due = stats.get("due", 0) or 0
                        # new in session is session_total minus due
                        new_in_session = (stats.get("session_total", 0) or 0) - due
                        
                        if due > 0 or new_in_session > 0:
                            meta = lang_meta.get(lang, {"flag": "🌐", "name": lang.upper()})
                            msg = f"🔔 <b>Time to practice!</b>\n\n"
                            msg += f"{meta['flag']} <b>{meta['name']}:</b> {due} review {new_in_session} new"
                            
                            user = await app['user_repo'].get_user(user_id)
                            username = user.get('name', f"ID {user_id}") if user else f"ID {user_id}"
                            
                            logger.info("Notification sent: %s [%s] (due: %d, new: %d)", username, lang, due, new_in_session)
                            await send_tg_push(token, chat_id, msg)
                            last_sent[sent_key] = today_key
                        else:
                            # Optional: more descriptive log for no words
                            pass
                            # Mark as "sent" anyway, so we don't keep checking every minute if the loop logic changes
                            last_sent[sent_key] = today_key

        except Exception as e:
            logger.error("Error in scheduler loop: %s", e)
            await asyncio.sleep(60)
