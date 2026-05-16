import asyncio
import logging
from aiohttp import web
from db.models import init_db
from db.user_repo import UserRepo
from db.word_repo import WordRepo
from api.auth import auth_middleware, no_cache_middleware
from api.routes import setup_routes
from core.scheduler import scheduler_loop
from core import config

logger = logging.getLogger(__name__)

async def on_startup(app: web.Application):
    """Initialize resources on startup."""
    db = await init_db(config.DB_PATH)
    app['db'] = db
    app['user_repo'] = UserRepo(db)
    app['word_repo'] = WordRepo(db, tz=config.APP_TZ)
    
    # Start the notification scheduler
    asyncio.create_task(scheduler_loop(app))
    
    logger.info("Database connection established: %s", config.DB_PATH)

async def on_cleanup(app: web.Application):
    """Gracefully close resources."""
    if 'db' in app:
        await app['db'].close()
        logger.info("Database connection closed")

def create_app() -> web.Application:
    """Factory to create the application instance."""
    instance = web.Application(middlewares=[no_cache_middleware, auth_middleware])
    
    # Register signals
    instance.on_startup.append(on_startup)
    instance.on_cleanup.append(on_cleanup)
    
    # Setup routes
    setup_routes(instance)
    
    # Serve static files
    instance.router.add_static('/static', './static')
    
    return instance
