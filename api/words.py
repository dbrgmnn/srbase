import logging
import os
from aiohttp import web

logger = logging.getLogger(__name__)

env_langs = os.getenv("ALLOWED_LANGS", "en,de")
ALLOWED_LANGS = {lang.strip() for lang in env_langs.split(",")}

class WordHandler:
    @staticmethod
    async def add_word(request: web.Request) -> web.Response:
        """Add a new word to the dictionary."""
        try:
            user_id = int(request["user_id"])
            data = await request.json()
            word = data.get("word", "").strip()
            translation = data.get("translation", "").strip()
            language = data.get("lang", "de").strip()
            example = data.get("example", "").strip() or None
            level = data.get("level", "").strip() or None

            if language not in ALLOWED_LANGS:
                return web.json_response({"status": "error", "message": "Unsupported language"}, status=400)

            if not word or not translation:
                return web.json_response({"status": "error", "message": "Word and translation required"}, status=400)

            repo = request.app["word_repo"]
            
            # Check if the word already exists (case-insensitive, ignoring translation)
            existing = await repo.get_word_by_text(user_id, language, word)
            if existing:
                return web.json_response({"status": "error", "message": "Word already exists"}, status=409)

            word_id = await repo.add_single_word(user_id, language, word, translation, example, level)
            
            if word_id:
                return web.json_response({"status": "ok", "id": word_id})
            return web.json_response({"status": "error", "message": "Word already exists"}, status=409)

        except Exception as e:
            logger.error("Add word error: %s", e)
            return web.json_response({"status": "error", "message": "Internal server error"}, status=500)

    @staticmethod
    async def update_word(request: web.Request) -> web.Response:
        """Update word text, translation, example, level."""
        try:
            user_id = int(request["user_id"])
            word_id = int(request.match_info["word_id"])
            data = await request.json()
            word = data.get("word", "").strip()
            translation = data.get("translation", "").strip()
            example = data.get("example", "").strip() or None
            level = data.get("level", "").strip() or None

            if not word or not translation:
                return web.json_response({"status": "error", "message": "Word and translation required"}, status=400)

            repo = request.app["word_repo"]
            try:
                ok = await repo.update_word_text(word_id, user_id, word, translation, example, level)
                if ok:
                    return web.json_response({"status": "ok"})
                return web.json_response({"status": "error", "message": "Word not found"}, status=404)
            except ValueError as e:
                if str(e) == "Duplicate word/translation":
                    return web.json_response({"status": "error", "message": "Word already exists"}, status=409)
                raise
        except Exception as e:
            logger.error("Update word error: %s", e)
            return web.json_response({"status": "error", "message": "Internal server error"}, status=500)

    @staticmethod
    async def delete_word(request: web.Request) -> web.Response:
        """Delete a word."""
        try:
            user_id = int(request["user_id"])
            word_id = int(request.match_info["word_id"])
            repo = request.app["word_repo"]
            await repo.delete_word(word_id, user_id)
            return web.json_response({"status": "ok"})
        except Exception as e:
            logger.error("Delete word error: %s", e)
            return web.json_response({"status": "error", "message": "Internal server error"}, status=500)

    @staticmethod
    async def search(request: web.Request) -> web.Response:
        try:
            # FORCE user_id to int to ensure SQLite matches INTEGER column
            user_id = int(request["user_id"])
            filter_type = request.query.get("filter", "").strip()
            language = str(request.query.get("lang", "de")).strip()
            query = request.query.get("q", "").strip()
            
            if language not in ALLOWED_LANGS:
                return web.json_response({"status": "error", "message": "Unsupported language"}, status=400)

            repo = request.app["word_repo"]
            
            if filter_type:
                logger.info("SEARCH FILTER: user=%d, lang=%s, filter=%s", user_id, language, filter_type)
                if filter_type in ["total", "difficult", "learning", "mastered"]:
                    words = await repo.get_words_by_status(user_id, language, filter_type)
                elif filter_type == "due":
                    words = await repo.get_session_words(user_id, language, 0)
                elif filter_type == "today_new":
                    words = await repo.get_today_words(user_id, language, "last_reviewed_at")
                elif filter_type == "today_added":
                    words = await repo.get_today_words(user_id, language, "created_at")
                else:
                    words = []
                
                return web.json_response({"status": "ok", "data": words})

            if not query: return web.json_response({"status": "ok", "data": []})
            words = await repo.search_words(user_id, language, query)
            return web.json_response({"status": "ok", "data": words})
        except Exception as e:
            logger.error("Search error: %s", e)
            return web.json_response({"status": "error", "message": "Internal server error"}, status=500)

    @staticmethod
    async def stats(request: web.Request) -> web.Response:
        try:
            user_id = int(request["user_id"])
            language = str(request.query.get("lang", "de")).strip()
            
            if language not in ALLOWED_LANGS:
                return web.json_response({"status": "error", "message": "Unsupported language"}, status=400)

            user_repo = request.app["user_repo"]
            settings = await user_repo.get_settings(user_id, language)
            daily_limit = settings.get("daily_limit", 20)
            repo = request.app["word_repo"]
            stats = await repo.get_full_stats(user_id, language, daily_limit=daily_limit)
            return web.json_response({"status": "ok", "data": stats})
        except Exception as e:
            logger.error("Stats error: %s", e)
            return web.json_response({"status": "error", "message": "Internal server error"}, status=500)

