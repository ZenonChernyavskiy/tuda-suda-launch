# Deployment Guide

Этот документ описывает путь от локального MVP до Telegram Mini App на собственном HTTPS-домене.

## 1. Подготовить сервер

Минимально:

- Ubuntu 22.04/24.04 или другой Linux server.
- Docker и Docker Compose plugin.
- Домен для frontend, например `app.example.com`.
- Домен для backend, например `api.example.com`.
- HTTPS через reverse proxy: Caddy, Nginx Proxy Manager, Traefik или nginx + certbot.

## 2. Создать Telegram Bot и Mini App

1. Откройте BotFather.
2. Создайте бота: `/newbot`.
3. Сохраните token в `TELEGRAM_BOT_TOKEN`.
4. Создайте Mini App для бота.
5. Укажите frontend HTTPS URL:

```text
https://app.example.com
```

6. Настройте menu button:

```text
/setmenubutton
```

7. Проверьте, что Mini App открывается внутри Telegram и передает `initData`.

## 3. Настроить production env

```bash
cd tuda-suda
cp .env.production.example .env.production
```

Заполните:

```env
APP_ENV=production
AUTO_INIT_DB=false
DATABASE_URL=postgresql+psycopg://tuda_suda:<password>@postgres:5432/tuda_suda
TELEGRAM_BOT_TOKEN=<bot token>
ALLOW_MOCK_AUTH=false
AUTH_TOKEN_SECRET=<long random secret>
ADMIN_API_KEY=<long random admin key>
CORS_ORIGINS=https://app.tudasuda.tech
PUBLIC_APP_URL=https://app.tudasuda.tech
PUBLIC_API_URL=https://api.tudasuda.tech
VITE_API_URL=https://api.tudasuda.tech
VITE_APP_URL=https://app.tudasuda.tech
VITE_TONCONNECT_MANIFEST_URL=https://app.tudasuda.tech/tonconnect-manifest.json
VITE_ENABLE_MOCK_AUTH=false
VITE_ENABLE_ADMIN=false
```

Для TON testnet deposits:

```env
PROJECT_TON_WALLET=UQB-gyjeCOixVUyVx-X_4FqhXeOwjCIUYnkue4vQESUx6f66
HOT_WALLET_ADDRESS=UQB-gyjeCOixVUyVx-X_4FqhXeOwjCIUYnkue4vQESUx6f66
TONCENTER_API_KEY=<optional key>
```

Комиссии сервиса:

```env
BUY_COMMISSION_PERCENT=1
TRANSFER_COMMISSION_PERCENT=10
TREASURY_WALLET_ADDRESS=UQAOgQnt-ZMtAsMWtnL9zFs1Id27b8L3gc35pvQZA4dmUZg6
```

`BUY_COMMISSION_PERCENT=1` удерживает 1% из TDSD-покупки перед финальным зачислением на внутренний баланс. `TRANSFER_COMMISSION_PERCENT=10` удерживает 10% из суммы TDSD-дара: отправитель списывает полную сумму, получатель получает 90%, treasury получает 10%.

Для TDSD после deploy Jetton:

```env
TDSD_JETTON_MASTER_ADDRESS=EQBZkfdol6WOj-GXByKLeRlo70ktYIQnTA5Hq_gT6KVYvY3n
TDSD_PROJECT_JETTON_WALLET=<Project Jetton Wallet>
TDSD_DEPOSITS_ENABLED=true
```

Пока контракт не развернут, оставьте:

```env
TDSD_DEPOSITS_ENABLED=false
```

## 4. Настроить TON Connect Manifest

Откройте:

```text
frontend/public/tonconnect-manifest.json
```

Замените placeholder:

```json
{
  "url": "https://app.tudasuda.tech",
  "name": "Tuda-Suda",
  "iconUrl": "https://app.tudasuda.tech/tonconnect-icon.svg"
}
```

`url` и `iconUrl` должны быть доступны по HTTPS.

## 5. Запустить Docker Compose

```bash
docker compose --env-file .env.production up --build -d
```

Проверить:

```bash
docker compose ps
docker compose logs backend --tail=100
```

Backend контейнер выполняет:

```bash
alembic upgrade head
python production_seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 6. Подключить домены

В reverse proxy:

- `https://api.tudasuda.tech` -> backend container `8000`
- `https://app.tudasuda.tech` -> frontend container `80`

Проверьте:

```text
https://api.tudasuda.tech/health
https://api.tudasuda.tech/ready
https://app.tudasuda.tech
https://app.tudasuda.tech/tonconnect-manifest.json
```

## 7. Проверить Mini App

1. Откройте бота в Telegram.
2. Нажмите menu button.
3. Приложение должно открыться без mock mode.
4. Backend должен принять `initData`.
5. На профиле подключите TON Connect wallet.
6. Сохраните wallet в backend.
7. Создайте TON testnet deposit.
8. Отправьте testnet TON с memo.
9. Нажмите “Проверить статус”.
10. Проверьте `AssetBalance` и `AssetLedgerEntry`.

## 8. Проверить TDSD

1. Подготовьте contract workspace:

```bash
cd contracts
npm install
cp .env.contracts.example .env.contracts
npm run build
npm test
```

2. Заполните в `contracts/.env.contracts`:

```env
TDSD_METADATA_URL=https://app.tudasuda.tech/tdsd-metadata.json
TDSD_OWNER_ADDRESS=<admin wallet>
TDSD_PROJECT_WALLET_ADDRESS=<project TON wallet owner>
```

3. Разверните TDSD Jetton Master в testnet:

```bash
npm run deploy:testnet
```

4. Проверьте getters:

```env
TDSD_JETTON_MASTER_ADDRESS=<master>
TDSD_WALLET_OWNER=<project TON wallet owner>
```

```bash
npm run get:data
```

5. Установите backend env:

```env
TDSD_JETTON_MASTER_ADDRESS=<master>
TDSD_PROJECT_JETTON_WALLET=<wallet>
TDSD_DEPOSITS_ENABLED=true
```

6. Перезапустите backend:

```bash
docker compose --env-file .env.production up --build -d backend
```

7. Проверьте `GET /ready` и `GET /assets`: TDSD должен быть активным.
8. Создайте TDSD deposit.
9. Отправьте TDSD на Project Jetton Wallet с memo.
10. Проверьте deposit.
11. Отправьте внутренний asset gift в TDSD.

## 9. Referral Program

Для referral-ссылок заполните backend env:

```env
REFERRALS_ENABLED=true
REFERRAL_REWARD_PERCENT=10
REFERRAL_REWARD_ASSET_SYMBOL=TDSD
TELEGRAM_BOT_USERNAME=rudasuda_tdsd_bot
TELEGRAM_MINI_APP_SHORT_NAME=<mini app short name или пусто>
FRONTEND_URL=https://app.tudasuda.tech
```

Если `TELEGRAM_MINI_APP_SHORT_NAME` пустой, ссылка будет вести в бота через
`?start=ref_<code>`. Если short name задан, ссылка будет вести прямо в Mini App
через `?startapp=ref_<code>`.

Награда начисляется только после подтвержденного TDSD `AssetDeposit`.
Повторное начисление за один deposit блокируется на backend.

## 10. Admin API

Admin endpoints требуют header:

```text
X-Admin-Token: <ADMIN_API_KEY>
```

Не включайте `VITE_ENABLE_ADMIN=true` в публичном frontend build.

## 11. Rollback

Если deploy не прошел:

```bash
docker compose logs backend --tail=200
docker compose down
```

Проверьте env validation error. Backend намеренно не стартует, если production env небезопасен.

## 12. Full E2E

Перед закрытым testnet launch пройдите полный сценарий из `E2E_TESTING.md`.
