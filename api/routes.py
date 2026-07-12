from aiohttp import web
from api.auth import UserHandler
from api.words import WordHandler
from api.practice import PracticeHandler


async def index_handler(_request):
    """Serve the main index.html file."""
    return web.FileResponse('./index.html')

def setup_routes(app: web.Application):
    # Main entry point
    app.router.add_get('/', index_handler)
    app.router.add_get('/sw.js', lambda _req: web.FileResponse('./sw.js'))

    # User routes
    app.router.add_get('/api/users/list', UserHandler.list_users)
    app.router.add_post('/api/users', UserHandler.access)
    app.router.add_get('/api/me', UserHandler.me)
    app.router.add_put('/api/me', UserHandler.update_me)
    app.router.add_delete('/api/me', UserHandler.delete_me)
    app.router.add_get('/api/me/settings', UserHandler.get_settings)
    app.router.add_put('/api/me/settings', UserHandler.update_settings)

    # Word routes
    app.router.add_get('/api/words/search', WordHandler.search)
    app.router.add_get('/api/words/stats', WordHandler.stats)
    app.router.add_post('/api/words', WordHandler.add_word)
    app.router.add_patch('/api/words/{word_id}', WordHandler.update_word)
    app.router.add_delete('/api/words/{word_id}', WordHandler.delete_word)

    # Practice routes
    app.router.add_get('/api/practice/session', PracticeHandler.get_session)
    app.router.add_post('/api/practice/answer', PracticeHandler.answer)
    app.router.add_post('/api/practice/undo', PracticeHandler.undo)
