import json
import logging
from aiohttp import web, ClientSession, ClientTimeout
from core import config

logger = logging.getLogger(__name__)

ALLOWED_CEFR = {"A1", "A2", "B1", "B2", "C1", "C2"}


def build_prompt(input_text: str, lang: str) -> str:
    return f"""You are a lexical validator and translator.

Language: {lang}
Input: {input_text}

Rules:
- If input is a German noun, return lowercase article + capitalized noun.
- word: normalized input word or phrase in the target language.
- translation: Russian translation in lowercase.
- level: CEFR level only: A1, A2, B1, B2, C1, C2.
- example: one natural {lang} sentence containing the exact word or phrase.
- is_valid: false if input is gibberish or not a real {lang} word or phrase, else true.
- If is_valid is false, return empty strings for word, translation, example, and level.
- Return only one JSON object and nothing else.

Return:
{{"word":"","translation":"","example":"","level":"","is_valid":true}}"""


def normalize_result(data: dict) -> dict:
    word = str(data.get("word", "")).strip()
    translation = str(data.get("translation", "")).strip().lower()
    example = str(data.get("example", "")).strip()
    level = str(data.get("level", "")).strip().upper()
    is_valid = bool(data.get("is_valid", False))

    if not is_valid or not word:
        return {
            "word": "",
            "translation": "",
            "example": "",
            "level": "",
            "is_valid": False,
        }

    if level not in ALLOWED_CEFR:
        level = ""

    return {
        "word": word,
        "translation": translation,
        "example": example,
        "level": level,
        "is_valid": True,
    }


class AIHandler:
    @staticmethod
    async def translate(request: web.Request) -> web.Response:
        try:
            if not config.GEMINI_API_KEY:
                return web.json_response(
                    {"status": "error", "message": "GEMINI_API_KEY is not configured"},
                    status=500
                )

            payload = await request.json()
            input_text = str(payload.get("input", "")).strip()
            lang = str(payload.get("lang", "de")).strip()

            if not input_text:
                return web.json_response(
                    {"status": "error", "message": "Input is required"},
                    status=400
                )

            if len(input_text) > 120:
                return web.json_response(
                    {"status": "error", "message": "Input is too long"},
                    status=400
                )

            if lang != "de":
                return web.json_response(
                    {"status": "error", "message": "Only German is supported for now"},
                    status=400
                )

            prompt = build_prompt(input_text, lang)

            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}"
            )

            body = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.1,
                    "maxOutputTokens": 200
                }
            }

            timeout = ClientTimeout(total=20)

            async with ClientSession(timeout=timeout) as session:
                async with session.post(url, json=body) as resp:
                    raw = await resp.json()

            candidates = raw.get("candidates", [])
            if not candidates:
                logger.error("Gemini returned no candidates: %s", raw)
                return web.json_response(
                    {"status": "error", "message": "AI returned empty response"},
                    status=502
                )

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts or "text" not in parts[0]:
                logger.error("Gemini returned invalid structure: %s", raw)
                return web.json_response(
                    {"status": "error", "message": "AI returned invalid response"},
                    status=502
                )

            text = parts[0]["text"].strip()

            try:
                ai_data = json.loads(text)
            except json.JSONDecodeError:
                logger.error("Failed to parse Gemini JSON: %s", text)
                return web.json_response(
                    {"status": "error", "message": "AI returned malformed JSON"},
                    status=502
                )

            result = normalize_result(ai_data)
            return web.json_response({"status": "ok", "data": result})

        except Exception as e:
            logger.error("AI translate error: %s", e)
            return web.json_response(
                {"status": "error", "message": "AI translation unavailable"},
                status=500
            )
