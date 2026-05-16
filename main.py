import logging
from aiohttp import web
from core import config
from core.factory import create_app

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    app = create_app()
    logger.info("Starting app on %s:%d", config.APP_HOST, config.APP_PORT)
    web.run_app(app, host=config.APP_HOST, port=config.APP_PORT)
