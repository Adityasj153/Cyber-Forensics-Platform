import asyncio

from app.db.session import engine


def run_async(coro_factory):
    """Run an async coroutine and dispose the loop-bound engine afterward.

    Celery (prefork) tasks run in a fresh event loop per invocation, but the
    global async SQLAlchemy engine builds a loop-bound asyncpg pool. Reusing
    that pool across separate asyncio.run() loops raises
    "Future attached to a different loop". Disposing the engine at the end of
    each task run forces a fresh pool in the new loop.
    """

    async def _wrap():
        try:
            await coro_factory()
        finally:
            await engine.dispose()

    asyncio.run(_wrap())
