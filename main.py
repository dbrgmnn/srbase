import asyncio
import logging

from aiohttp import web
from db.models import init_db
from db.user_repo import UserRepo
from db.word_repo import WordRepo
from api.auth import auth_middleware
from api.routes import setup_routes
from core.scheduler import scheduler_loop
from core import config

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
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

async def index_handler(_request):
    """Serve the main index.html file."""
    return web.FileResponse('./index.html')

@web.middleware
async def no_cache_middleware(request, handler):
    response = await handler(request)
    if isinstance(response, web.Response):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

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
    instance.router.add_get('/', index_handler)
    
    return instance

if __name__ == "__main__":
    my_app = create_app()
    logger.info("Starting app on %s:%d", config.APP_HOST, config.APP_PORT)
    web.run_app(my_app, host=config.APP_HOST, port=config.APP_PORT)
