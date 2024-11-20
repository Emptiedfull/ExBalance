import asyncio
from aiohttp import web

async def handle(request):
    return web.Response(text="Hello, world")

async def init_app():
    app = web.Application()
    app.router.add_get('/', handle)
    return app

def main():
    port = 8000
    app = init_app()
    web.run_app(app, port=port)
    print(f"Server running on port {port}")

if __name__ == "__main__":
    main()