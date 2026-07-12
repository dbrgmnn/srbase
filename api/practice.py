import logging
from aiohttp import web
from core.srs import sm2
from api.words import ALLOWED_LANGS


logger = logging.getLogger(__name__)

class PracticeHandler:
    @staticmethod
    async def get_session(request: web.Request) -> web.Response:
        """Fetch words for a practice session based on user settings."""
        try:
            user_id = request["user_id"]
            language = request.query.get("lang", "de").strip()
            
            if language not in ALLOWED_LANGS:
                return web.json_response({"status": "error", "message": "Unsupported language"}, status=400)

            # Fetch daily limit from settings
            user_repo = request.app["user_repo"]
            settings = await user_repo.get_settings(user_id, language)
            limit = settings.get("daily_limit", 20)
            
            # We check how many new words were already started today
            word_repo = request.app["word_repo"]
            stats = await word_repo.get_full_stats(user_id, language, daily_limit=limit, tz=request.get("tz"))
            
            # new_limit is the number of "fresh" words we can add to the session
            new_limit = max(0, limit - stats.get("today_new", 0))
            
            words = await word_repo.get_session_words(user_id, language, new_limit=new_limit)
            
            return web.json_response({"status": "ok", "message": "Session words retrieved", "data": words})
        except Exception as e:
            logger.error("Session error: %s", e)
            return web.json_response({"status": "error", "message": "Internal server error"}, status=500)

    @staticmethod
    async def answer(request: web.Request) -> web.Response:
        """Submit an answer for a word and update its SRS data."""
        try:
            user_id = request["user_id"]
            data = await request.json()
            word_id = data.get("word_id")
            quality = data.get("quality") # 0-5 (0=forgot, 5=perfect)

            if word_id is None or quality is None:
                return web.json_response({"status": "error", "message": "Missing data"}, status=400)

            if not isinstance(quality, int) or not (0 <= quality <= 5):
                return web.json_response({"status": "error", "message": "quality must be integer 0–5"}, status=400)

            # Simple SRS logic
            repo = request.app["word_repo"]
            word = await repo.get_word(word_id, user_id)
            if not word:
                return web.json_response({"status": "error", "message": "Word not found"}, status=404)

            # Use centralized SM-2 Implementation
            result = sm2(
                quality=quality,
                repetitions=word.get('repetitions', 0),
                easiness=word.get('easiness', 2.5),
                interval=word.get('interval', 0)
            )
            
            await repo.update_word_after_review(
                user_id, 
                word_id, 
                result.repetitions, 
                result.easiness, 
                result.interval, 
                result.next_review
            )

            return web.json_response({"status": "ok", "message": "Answer processed", "next_review": result.next_review})

        except Exception as e:
            logger.error("Answer error: %s", e)
            return web.json_response({"status": "error", "message": "Internal server error"}, status=500)

    @staticmethod
    async def undo(request: web.Request) -> web.Response:
        """Revert word to its previous SRS state."""
        try:
            user_id = request["user_id"]
            data = await request.json()
            word_id = data.get("word_id")
            
            if not word_id:
                return web.json_response({"status": "error", "message": "Missing word_id"}, status=400)

            repo = request.app["word_repo"]
            await repo.undo_word_review(
                user_id=user_id,
                word_id=word_id,
                repetitions=data.get("repetitions", 0),
                easiness=data.get("easiness", 2.5),
                interval=data.get("interval", 0),
                next_review=data.get("next_review"),
                last_reviewed_at=data.get("last_reviewed_at"),
                started_at=data.get("started_at")
            )

            return web.json_response({"status": "ok", "message": "Review undone"})
        except Exception as e:
            logger.error("Undo error: %s", e)
            return web.json_response({"status": "error", "message": "Internal server error"}, status=500)
