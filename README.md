# Ortflix Telegram Bot

[![Lint - Ortflix Telegram](https://github.com/okdesign21/ortflix-telegram/actions/workflows/lint.yml/badge.svg)](https://github.com/okdesign21/ortflix-telegram/actions/workflows/lint.yml)
[![Security - Ortflix Telegram](https://github.com/okdesign21/ortflix-telegram/actions/workflows/security.yml/badge.svg)](https://github.com/okdesign21/ortflix-telegram/actions/workflows/security.yml)
[![Tag & Publish - Telegram](https://github.com/okdesign21/ortflix-telegram/actions/workflows/release.yml/badge.svg)](https://github.com/okdesign21/ortflix-telegram/actions/workflows/release.yml)

Telegram bot service for Overseerr/Jellyseerr notifications and request approvals.

## Features

- FastAPI webhook service for Seerr and optional media-integrity payloads
- Telegram notifications for `MEDIA_PENDING`, `MEDIA_AVAILABLE`, `MEDIA_FAILED`, and related types
- **Request quality profile** on pending, failed, and available notifications (resolved via Seerr API when the webhook includes a request id)
- **`MEDIA_AVAILABLE` for movies:** optional **downloaded file quality** and **on-disk folder** via the Radarr API (`tmdbId` in the webhook `media` object)
- Inline approve/decline for pending requests
- `GET /health` and typed Pydantic models

## Quick Start

```bash
git clone https://github.com/okdesign21/ortflix-telegram.git
cd ortflix-telegram
cp .env.example .env
./run-local.sh
```

## Environment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `TELEGRAM_TOKEN` | Yes | - | Telegram bot token from BotFather |
| `OVERSEERR_API_KEY` | Yes | - | Overseerr/Seerr API key |
| `TELEGRAM_CHAT_ID` | Yes | - | Telegram chat/user ID |
| `OVERSEERR_URL` | No | `http://seerr:5055` | Seerr base URL, or set `OVERSEERR_HOST` + `OVERSEERR_PORT` instead |
| `WEBHOOK_HOST` | No | `0.0.0.0` | Bind host for FastAPI |
| `WEBHOOK_PORT` | No | `7777` | Webhook service port |
| `WEBHOOK_TOKEN` | No | - | Optional webhook auth token |
| `RADARR_URL` | No | `http://radarr:7878` | Radarr base URL (no trailing slash), or `RADARR_HOST` + `RADARR_PORT` — same rules as `OVERSEERR_URL` |
| `RADARR_API_KEY` | No | - | Radarr API key; if unset, `MEDIA_AVAILABLE` omits downloaded quality and movie folder |

Defaults assume the bot runs on the **same Docker Compose network or Kubernetes namespace** as Seerr and Radarr (short names `seerr:5055` and `radarr:7878`). Set `OVERSEERR_URL` / `RADARR_URL` (or host/port vars) only when you use a different host, port, or external URL.

Seerr must be reachable for profile enrichment. Radarr is only used to decorate **movie** `MEDIA_AVAILABLE` messages; pending and failed flows do not call Radarr.

## API Endpoints

- `GET /health`
- `POST /api/v1/webhooks/overseerr`
- `POST /api/v1/webhooks/media-check`

When `WEBHOOK_TOKEN` is set, send it in the `x-webhook-token` header.

## Development

```bash
./run-local.sh test
./run-local.sh lint
./run-local.sh format
```

### Webhook Test

```bash
curl -X POST http://localhost:7777/api/v1/webhooks/overseerr \
  -H "Content-Type: application/json" \
  -d '{"notification_type":"MEDIA_PENDING","subject":"Test","request":{"request_id":"123"}}'
```

## Docker

```bash
docker build -t ortflix-telegram-bot .
docker run --rm \
  -e TELEGRAM_TOKEN="your_token" \
  -e OVERSEERR_API_KEY="your_key" \
  -e TELEGRAM_CHAT_ID="your_chat_id" \
  -e RADARR_API_KEY="your_radarr_key" \
  -p 7777:7777 \
  ortflix-telegram-bot
```

On the default bridge network, pass `OVERSEERR_URL` and `RADARR_URL` (e.g. `http://host.docker.internal:5055`). On a user-defined compose network with services named `seerr` and `radarr`, you can omit those URLs and only set `RADARR_API_KEY` when you want folder/quality on `MEDIA_AVAILABLE`.

## CI/CD

- `lint.yml` — lint and formatting checks
- `security.yml` — secret and vulnerability scans
- `release.yml` — tag-driven package/image publish and GitHub release

## Related Repositories

- Main stack: [`ortflix`](https://github.com/okdesign21/ortflix)
- Kometa and Tautulli automation: [`ortflix-costume`](https://github.com/okdesign21/ortflix-costume)

## License

MIT. See [`LICENSE`](LICENSE).
