# Ortflix Telegram Bot

[![Lint - Ortflix Telegram](https://github.com/okdesign21/ortflix-telegram/actions/workflows/lint.yml/badge.svg)](https://github.com/okdesign21/ortflix-telegram/actions/workflows/lint.yml)
[![Security - Ortflix Telegram](https://github.com/okdesign21/ortflix-telegram/actions/workflows/security.yml/badge.svg)](https://github.com/okdesign21/ortflix-telegram/actions/workflows/security.yml)
[![Tag & Publish - Telegram](https://github.com/okdesign21/ortflix-telegram/actions/workflows/release.yml/badge.svg)](https://github.com/okdesign21/ortflix-telegram/actions/workflows/release.yml)

Telegram bot service for Overseerr/Seerr notifications and request approvals.

This is the only Ortflix repository that publishes GitHub releases, triggered by tags matching `v*`.

## Features

- FastAPI webhook service
- Telegram notifications for request events
- Inline approve/decline actions
- Health endpoint at `GET /health`
- Async architecture with typed payload models

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
| `OVERSEERR_URL` | No | `http://seerr:5055` | Overseerr/Seerr base URL |
| `WEBHOOK_HOST` | No | `0.0.0.0` | Bind host for FastAPI |
| `WEBHOOK_PORT` | No | `7777` | Webhook service port |
| `WEBHOOK_TOKEN` | No | - | Optional webhook auth token |

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
  -p 7777:7777 \
  ortflix-telegram-bot
```

## CI/CD

- `lint.yml` — lint and formatting checks
- `security.yml` — secret and vulnerability scans
- `release.yml` — tag-driven package/image publish and GitHub release

## Related Repositories

- Main stack: [`ortflix`](https://github.com/okdesign21/ortflix)
- Kometa and Tautulli automation: [`ortflix-costume`](https://github.com/okdesign21/ortflix-costume)

## License

MIT. See [`LICENSE`](LICENSE).
