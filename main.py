import asyncio
import logging
import os
from aiohttp import web
from db.models import init_db
from db.user_repo import UserRepo
from db.word_repo import WordRepo
from api.auth import auth_middleware
from api.routes import setup_routes
from core.scheduler import scheduler_loop

# Load .env file manually if it exists
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "srbase.db")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", 8080))

async def on_startup(app: web.Application):
    """Initialize resources on startup."""
    db = await init_db(DB_PATH)
    app['db'] = db
    app['user_repo'] = UserRepo(db)
    app['word_repo'] = WordRepo(db)
    
    # Start the notification scheduler
    asyncio.create_task(scheduler_loop(app))
    
    logger.info("Database connection established: %s", DB_PATH)

async def on_cleanup(app: web.Application):
    """Gracefully close resources."""
    if 'db' in app:
        await app['db'].close()
        logger.info("Database connection closed")

async def index_handler(_request):
    """Serve the main index.html file."""
    return web.FileResponse('./index.html')

def create_app() -> web.Application:
    """Factory to create the application instance."""
    instance = web.Application(middlewares=[auth_middleware])
    
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
    logger.info("Starting app on %s:%d", APP_HOST, APP_PORT)
    web.run_app(my_app, host=APP_HOST, port=APP_PORT)
