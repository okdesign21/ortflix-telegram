"""Simplified Telegram Bot for Ortflix - Overseerr integration.

Handles webhooks and callback queries using extensible handler registry.
"""

import datetime
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

import aiohttp
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, status
from pydantic import ValidationError
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler

from config import (
    CALLBACK_HANDLERS,
    OVERSEERR_API_KEY,
    OVERSEERR_URL,
    TELEGRAM_PORT,
    TELEGRAM_TOKEN,
    WEBHOOK_HOST,
    WEBHOOK_TOKEN,
    get_telegram_chat_id,
    register_callback_handler,
    validate_config,
)
from models import (
    MediaIntegrityWebhook,
    OverseerrWebhook,
)
from payloads import _normalize_overseerr_payload, _normalize_request_keys

# === LOGGING ===
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# === GLOBAL STATE ===
app_telegram: Optional[Application] = None
bot: Optional[Bot] = None
TELEGRAM_CHAT_ID = None
request_queue = []
processing = False
corrupted_files_cache = {}


# === LIFECYCLE MANAGEMENT ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage FastAPI application lifecycle."""
    global app_telegram, bot, TELEGRAM_CHAT_ID

    # Validate and initialize
    validate_config()
    TELEGRAM_CHAT_ID = get_telegram_chat_id()

    # Startup
    logger.info("Initializing Telegram bot application...")
    app_telegram = Application.builder().token(TELEGRAM_TOKEN).build()
    bot = app_telegram.bot

    # Add handlers
    app_telegram.add_handler(CallbackQueryHandler(callback_query_handler))

    # Initialize application
    await app_telegram.initialize()
    await app_telegram.start()

    if app_telegram.updater:
        await app_telegram.updater.start_polling(allowed_updates=["callback_query"])
        logger.info("Telegram polling started for callback queries")

    logger.info("Telegram bot initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down Telegram bot...")
    if app_telegram:
        if app_telegram.updater:
            await app_telegram.updater.stop()
        await app_telegram.stop()
        await app_telegram.shutdown()
    logger.info("Telegram bot shut down successfully")


# === FASTAPI APP ===
app = FastAPI(
    title="Ortflix Telegram Bot API",
    description="REST API for handling Overseerr and media integrity webhooks",
    version="2.0.0",
    lifespan=lifespan,
)


# === API HELPERS ===
async def call_overseerr_api(endpoint: str, method: str = "POST", json_data: dict = None) -> dict:
    """Make an API call to Overseerr."""
    session = aiohttp.ClientSession()
    try:
        method_upper = method.upper()
        request_func = {
            "GET": session.get,
            "POST": session.post,
            "PUT": session.put,
            "DELETE": session.delete,
        }.get(method_upper, session.request)

        async with request_func(
            f"{OVERSEERR_URL}{endpoint}",
            json=json_data,
            headers={
                "X-Api-Key": OVERSEERR_API_KEY,
                "Content-Type": "application/json",
            },
        ) as response:
            if response.status >= 400:
                error_text = await response.text()
                raise Exception(f"Overseerr API error {response.status}: {error_text}")
            body = await response.text()
            if not body:
                return {}
            return json.loads(body)
    finally:
        close_result = session.close()
        if hasattr(close_result, "__await__"):
            await close_result


async def call_overseerr(request_id: str, action: str) -> None:
    """Call Overseerr API to approve or decline a request."""
    await call_overseerr_api(f"/api/v1/request/{request_id}/{action}")


def _webhook_request_id(data: dict) -> Optional[str]:
    """Resolve request id from embedded request or top-level template field."""
    req = data.get("request")
    if isinstance(req, dict):
        rid = req.get("request_id") or req.get("id")
        if rid is not None:
            return str(rid)
    top = data.get("request_id")
    if top is not None:
        return str(top)
    return None


async def _enrich_payload_with_seerr_request(data: dict) -> dict:
    """Fill profile fields from Seerr API when the webhook body omits them.

    Webhooks often lack `profileName`; single-request GET also omits it, so we
    resolve the name via GET /service/radarr|sonarr/{serverId} when possible.
    """
    nt = data.get("notification_type")
    if nt not in ("MEDIA_PENDING", "MEDIA_FAILED"):
        return data

    rid = _webhook_request_id(data)
    if not rid:
        return data

    req_layer: dict[str, Any] = dict(data.get("request") or {})
    try:
        api_req = await call_overseerr_api(f"/api/v1/request/{rid}", method="GET")
    except Exception as err:
        logger.warning("Seerr request %s fetch failed (profile enrichment): %s", rid, err)
        return data

    merged_req = {**api_req, **req_layer}
    if merged_req.get("id") is not None and merged_req.get("request_id") is None:
        merged_req["request_id"] = merged_req["id"]
    merged_req = _normalize_request_keys(merged_req)

    pid = merged_req.get("profileId")
    sid = merged_req.get("serverId")
    name = merged_req.get("profileName") or merged_req.get("profile_name")
    media = merged_req.get("media") if isinstance(merged_req.get("media"), dict) else {}
    rtype = merged_req.get("type") or media.get("mediaType") or media.get("media_type") or "movie"

    if name is None and pid is not None and sid is not None:
        try:
            if rtype == "tv":
                svc = await call_overseerr_api(f"/api/v1/service/sonarr/{sid}", method="GET")
            else:
                svc = await call_overseerr_api(f"/api/v1/service/radarr/{sid}", method="GET")
            for p in svc.get("profiles") or []:
                if p.get("id") == pid:
                    merged_req["profileName"] = p.get("name")
                    break
        except Exception as err:
            logger.debug("Profile name resolve failed: %s", err)

    out = {**data, "request": merged_req}
    return out


async def send_photo_or_message(image: Optional[str], caption: str, reply_markup=None) -> None:
    """Send a photo (if provided) or a text message to Telegram."""
    if not bot:
        raise RuntimeError("Bot not initialized")

    send_func = bot.send_photo if image else bot.send_message
    kwargs = {
        "chat_id": TELEGRAM_CHAT_ID,
        "parse_mode": "Markdown",
        "reply_markup": reply_markup,
    }

    if image:
        kwargs["photo"] = image
        kwargs["caption"] = caption
    else:
        kwargs["text"] = caption

    await send_func(**kwargs)


# === REQUEST QUEUE ===
async def process_queue() -> None:
    """Process the request queue."""
    global processing
    if processing or not request_queue or not bot:
        return

    processing = True
    queue_item = request_queue.pop(0)
    request_id = queue_item["request_id"]
    action = queue_item["action"]
    chat_id = queue_item["chat_id"]
    callback_id = queue_item["callback_id"]

    try:
        await bot.answer_callback_query(callback_id, text=f"Processing request {request_id}...")
        await call_overseerr(request_id, action)
        message = f"✅ Request {request_id} has been {action}d."
        logger.info(f"Request {request_id} {action}d successfully")
    except Exception as err:
        logger.error(f"Error processing request {request_id}: {err}")
        await bot.answer_callback_query(callback_id, text=f"❌ Failed to {action} request")
        message = f"❌ Failed to {action} request {request_id}."

    await bot.send_message(chat_id, message)
    processing = False

    if request_queue:
        await process_queue()


# === CALLBACK HANDLERS (extensible) ===
async def handle_approve_decline(action: str, parts: list[str], chat_id: int, query) -> None:
    """Handle approve/decline actions."""
    if len(parts) != 2:
        return
    request_id = parts[1]
    request_queue.append(
        {
            "request_id": request_id,
            "action": action,
            "chat_id": chat_id,
            "callback_id": query.id,
        }
    )
    await process_queue()


async def handle_redownload(parts: list[str], chat_id: int, query) -> None:
    """Create and auto-approve a redownload request in Overseerr."""
    if len(parts) != 3 or not bot:
        return

    media_type, media_id = parts[1], parts[2]

    try:
        await query.answer(text="🔄 Creating redownload request...")

        result = await call_overseerr_api(
            "/api/v1/request", json_data={"mediaType": media_type, "mediaId": int(media_id)}
        )

        request_id = result.get("id")
        if not request_id:
            raise Exception("No request ID returned")

        await call_overseerr_api(f"/api/v1/request/{request_id}/approve")

        logger.info(f"Redownload request {request_id} created and auto-approved")
        await bot.send_message(
            chat_id, f"✅ Redownload request created and approved!\nRequest ID: {request_id}"
        )

    except Exception as err:
        logger.error(f"Redownload request failed: {err}")
        await query.answer(text="❌ Failed to create redownload request", show_alert=True)
        await bot.send_message(chat_id, f"❌ Redownload request failed: {err}")


async def handle_show_corrupted_files(parts: list[str], chat_id: int, query) -> None:
    """Show cached corrupted file details with action buttons."""
    if len(parts) < 3 or not bot:
        return

    await query.answer(text="📋 Loading details...")

    latest_key = next(
        (
            k
            for k in sorted(corrupted_files_cache.keys(), reverse=True)
            if k.startswith("corrupted_")
        ),
        None,
    )

    if not latest_key:
        await bot.send_message(chat_id, "❌ Corrupted files data not found")
        return

    cached_data = corrupted_files_cache[latest_key]
    files, count = cached_data["files"], cached_data["count"]
    max_display = 20

    details_msg = f"🔴 *Corrupted Files - {count} Issues*\n\n"
    details_msg += "\n".join(
        f"{i}. `{f['path']}`\n   📏 {f['size']} | ❌ {f['error']}"
        for i, f in enumerate(files[:max_display], 1)
    )

    if len(files) > max_display:
        details_msg += f"\n\n... and {len(files) - max_display} more files"

    details_msg += "\n\n*Options:*"

    reply_markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⬇️ Redownload All", callback_data="redownload_all_corrupted")],
            [InlineKeyboardButton("⬇️ Redownload Selected", callback_data="redownload_selected")],
            [InlineKeyboardButton("✖️ Close", callback_data="dismiss")],
        ]
    )

    await bot.send_message(
        chat_id, text=details_msg, parse_mode="Markdown", reply_markup=reply_markup
    )


async def handle_dismiss(parts: list[str], query) -> None:
    """Dismiss an alert message."""
    if len(parts) != 2:
        return

    await query.answer(text="✖️ Alert dismissed")
    try:
        await query.message.delete()
    except Exception as err:
        logger.debug("Unable to delete alert message: %s", err)


# Register built-in callback handlers
register_callback_handler("approve", handle_approve_decline)
register_callback_handler("decline", handle_approve_decline)
register_callback_handler("redownload", handle_redownload)
register_callback_handler("show", handle_show_corrupted_files)
register_callback_handler("dismiss", handle_dismiss)


# === CALLBACK QUERY HANDLER ===
async def callback_query_handler(update, context) -> None:
    """Dispatch callback queries to registered handlers."""
    query = update.callback_query
    if not query.data:
        return

    logger.info("Callback query received: %s", query.data)

    parts = query.data.split("_")
    if len(parts) < 2:
        return

    action = parts[0]
    chat_id = query.message.chat.id

    handler = CALLBACK_HANDLERS.get(action)
    if handler:
        await handler(action, parts, chat_id, query)


# === REST API ENDPOINTS ===
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "bot_initialized": bot is not None,
        "telegram_connected": app_telegram is not None,
    }


@app.post("/api/v1/webhooks/overseerr")
async def overseerr_webhook(
    request: Request,
    x_webhook_token: Optional[str] = Header(None),
):
    """Handle Overseerr webhook notifications.

    Supports any registered notification type from WEBHOOK_HANDLERS registry.
    """
    try:
        try:
            raw_payload = await request.json()
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            ) from err

        logger.debug(f"Raw Overseerr payload: {raw_payload}")

        normalized_payload = _normalize_overseerr_payload(raw_payload)
        logger.debug(f"Normalized payload: {normalized_payload}")

        try:
            payload = OverseerrWebhook.model_validate(normalized_payload)
        except ValidationError as err:
            logger.error("Overseerr webhook validation error: %s", err)
            logger.debug(f"Failed to validate normalized payload: {normalized_payload}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid Overseerr webhook payload",
            ) from err
        logger.info(f"Received Overseerr webhook: {payload.notification_type}")
        logger.debug(f"Parsed payload: type={payload.notification_type}, subject={payload.subject}")

        # Verify webhook token if configured
        if WEBHOOK_TOKEN and x_webhook_token != WEBHOOK_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook token",
            )

        # Dispatch to registered handler
        from config import WEBHOOK_HANDLERS

        handler_info = WEBHOOK_HANDLERS.get(payload.notification_type)
        if not handler_info:
            logger.info(f"Unhandled notification type: {payload.notification_type}")
            return {"status": "ok"}

        working_payload = await _enrich_payload_with_seerr_request(normalized_payload)
        caption = handler_info["caption"](working_payload)
        logger.debug(f"Built caption: {caption}")

        reply_markup = None
        if handler_info["reply_markup"]:
            reply_markup = handler_info["reply_markup"](working_payload)
            logger.debug("Built reply_markup with buttons")

        await send_photo_or_message(
            payload.image,
            caption,
            reply_markup=reply_markup,
        )

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Webhook handling error: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from err


@app.post("/api/v1/webhooks/media-check")
async def media_integrity_webhook(payload: MediaIntegrityWebhook):
    """Handle media integrity check alerts."""
    try:
        if payload.notification_type != "CORRUPTION_DETECTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid notification type",
            )

        if payload.count == 0:
            logger.info("Media check: no corrupted files found")
            return {"status": "ok"}

        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📋 View Details",
                        callback_data=f"show_corrupted_files_{payload.count}",
                    ),
                ],
            ]
        )

        cache_key = f"corrupted_{payload.count}_{int(datetime.datetime.now().timestamp())}"
        corrupted_files_cache[cache_key] = {
            "files": [file.model_dump() for file in payload.files],
            "count": payload.count,
        }

        if bot:
            await bot.send_message(
                TELEGRAM_CHAT_ID,
                text=payload.summary_message,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )

        logger.info(f"Sent media integrity summary: {payload.count} corrupted files")
        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Media check webhook error: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from err


def main():
    """Main function to start FastAPI server with Telegram bot integration."""
    logger.info(f"Starting Ortflix Telegram Bot API on {WEBHOOK_HOST}:{TELEGRAM_PORT}")

    uvicorn.run(
        app,
        host=WEBHOOK_HOST,
        port=TELEGRAM_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
