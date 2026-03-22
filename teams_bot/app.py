"""Webhook server for the Agility AI Teams bot.

Teams POSTs every incoming message to /api/messages.  The Bot Framework
adapter verifies the JWT signature, deserialises the Activity, and hands it
to AgilityBot.on_turn().

Environment variables
---------------------
MICROSOFT_APP_ID       — App ID from Azure Bot registration (blank = dev mode)
MICROSOFT_APP_PASSWORD — Client secret from Azure Bot registration
BOT_PORT               — Port to listen on (default 3978)
AGILITY_API_URL        — Base URL of the FastAPI backend (default http://localhost:8000)
BOT_API_TIMEOUT_SECONDS — Seconds to wait for a backend response (default 30)
LOG_LEVEL              — Python log level (default INFO)
"""

import logging
import os

from aiohttp import web
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity

from bot import AgilityBot

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

APP_ID = os.getenv("MICROSOFT_APP_ID", "")
APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD", "")

adapter = BotFrameworkAdapter(BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD))
bot = AgilityBot()


async def messages(req: web.Request) -> web.Response:
    """Primary webhook endpoint — Teams sends every message here."""
    content_type = req.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        return web.Response(status=415, text="Expected application/json")

    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    try:
        invoke_response = await adapter.process_activity(activity, auth_header, bot.on_turn)
        if invoke_response:
            return web.json_response(data=invoke_response.body, status=invoke_response.status)
        return web.Response(status=201)
    except Exception as exc:
        logger.exception("Error processing Teams activity")
        return web.Response(status=500, text=str(exc))


async def health(_req: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health)
    return app


if __name__ == "__main__":
    port = int(os.getenv("BOT_PORT", "3978"))
    logger.info("Starting Agility AI Teams bot on port %d", port)
    web.run_app(build_app(), host="0.0.0.0", port=port)
