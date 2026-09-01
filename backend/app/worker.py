from __future__ import annotations

import asyncio
import logging

from .queue import stop, worker_loop


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(_run())


async def _run() -> None:
    try:
        await worker_loop()
    finally:
        await stop()


if __name__ == "__main__":
    main()
