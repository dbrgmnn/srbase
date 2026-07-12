import logging
from aiohttp import web
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


logger = logging.getLogger(__name__)

@web.middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except web.HTTPException as ex:
        if ex.status >= 400:
            return web.json_response(
                {"status": "error", "message": ex.reason},
                status=ex.status
            )
        raise
    except Exception as e:
        logger.error("Unhandled exception: %s", e)
        return web.json_response(
            {"status": "error", "message": "Internal server error"},
            status=500
        )

@web.middleware
async def no_cache_middleware(request, handler):
    response = await handler(request)
    if isinstance(response, web.Response):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@web.middleware
async def auth_middleware(request, handler):
    """Middleware for identity management via X-User-Id header."""
    if request.path == "/" or request.path.startswith("/static/") or request.path in ["/api/users", "/api/users/list"]:
        return await handler(request)

    user_id_str = request.headers.get("X-User-Id")
    
    if not user_id_str:
        return web.json_response({"status": "error", "message": "Unauthorized: X-User-Id header missing"}, status=401)

    try:
        user_id = int(user_id_str)
        # Verify user existence in DB
        repo = request.app["user_repo"]
        user = await repo.get_user(user_id)
        if not user:
            return web.json_response({"status": "error", "message": "Unauthorized: User does not exist"}, status=401)
            
        request["user_id"] = user_id
    except ValueError:
        return web.json_response({"status": "error", "message": "Invalid user ID format"}, status=400)

    tz_str = request.headers.get("X-Timezone", "UTC")
    try:
        request["tz"] = ZoneInfo(tz_str)
    except ZoneInfoNotFoundError:
        request["tz"] = ZoneInfo("UTC")

    return await handler(request)

class UserHandler:
    """Simple user management logic."""

    @staticmethod
    async def list_users(request: web.Request) -> web.Response:
        """Get all registered users."""
        users = await request.app["user_repo"].list_users()
        return web.json_response({"status": "ok", "message": "Users retrieved", "data": users})


    @staticmethod
    async def access(request: web.Request) -> web.Response:
        """Get or create a user by email (unified access point)."""
        try:
            data = await request.json()
            email = data.get("email", "").strip().lower()
            name = data.get("name", "").strip()

            if not email:
                return web.json_response({"status": "error", "message": "Email required"}, status=400)

            repo = request.app["user_repo"]
            user = await repo.get_user_by_email(email)

            if not user:
                if not name:
                    return web.json_response({"status": "error", "message": "User not found, name required"}, status=404)
                user_id = await repo.create_user(name, email)
                user = {"id": user_id, "name": name, "email": email}

            return web.json_response({"status": "ok", "message": "User access granted", "user": dict(user)})

        except Exception as e:
            logger.error("User access error: %s", e)
            return web.json_response({"status": "error", "message": "Internal server error"}, status=500)

    @staticmethod
    async def me(request: web.Request) -> web.Response:
        """Retrieve current user information."""
        user_id = request["user_id"]
        user = await request.app["user_repo"].get_user(user_id)
        if not user:
            return web.json_response({"status": "error", "message": "User not found"}, status=404)
        return web.json_response({"status": "ok", "message": "User information retrieved", "user": user})

    @staticmethod
    async def delete_me(request: web.Request) -> web.Response:
        """Delete the current user account."""
        user_id = request["user_id"]
        repo = request.app["user_repo"]
        await repo.delete_user(user_id)
        return web.json_response({"status": "ok", "message": "User deleted"})

    @staticmethod
    async def update_me(request: web.Request) -> web.Response:
        """Update the current user profile (name, email, and telegram_chat_id)."""
        user_id = request["user_id"]
        data = await request.json()
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        
        repo = request.app["user_repo"]

        if name:
            await repo.update_user_name(user_id, name)
            
        if email:
            # Check if email is already taken by another user
            existing_user = await repo.get_user_by_email(email)
            if existing_user and existing_user["id"] != user_id:
                return web.json_response({"status": "error", "message": "Email already in use"}, status=400)
            await repo.update_user_email(user_id, email)
            
        if "telegram_chat_id" in data:
            telegram_chat_id = data.get("telegram_chat_id")
            val = telegram_chat_id.strip() if telegram_chat_id else None
            if val == "":
                val = None
            await repo.update_user_telegram_chat_id(user_id, val)
            
        if not name and not email and "telegram_chat_id" not in data:
            return web.json_response({"status": "error", "message": "Name, email or telegram_chat_id required"}, status=400)
            
        return web.json_response({"status": "ok", "message": "User updated"})

    @staticmethod
    async def get_settings(request: web.Request) -> web.Response:
        """Get settings for a specific language."""
        user_id = request["user_id"]
        lang = request.query.get("lang", "de").strip()
        settings = await request.app["user_repo"].get_settings(user_id, lang)
        return web.json_response({"status": "ok", "message": "Settings retrieved", "settings": settings})

    @staticmethod
    async def update_settings(request: web.Request) -> web.Response:
        """Update settings for a specific language."""
        user_id = request["user_id"]
        data = await request.json()
        lang = data.get("lang", "de").strip()
        limit = data.get("daily_limit")
        notif_time = data.get("notification_time")
        notif_threshold = data.get("notification_threshold")
        
        await request.app["user_repo"].update_settings(
            user_id, lang,
            daily_limit=limit,
            notification_time=notif_time,
            notification_threshold=notif_threshold,
        )
        return web.json_response({"status": "ok", "message": "Settings updated"})
