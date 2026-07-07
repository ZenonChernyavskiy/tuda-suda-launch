# Deployment Guide

Этот документ описывает путь от локального MVP до Telegram Mini App на собственном HTTPS-домене.

## 1. Подготовить сервер

Минимально:

- Ubuntu 22.04/24.04 или другой Linux server.
- Docker и Docker Compose plugin.
- Домен для frontend, например `app.tudasuda.tech`.
- Домен для backend, например `api.tudasuda.tech`.
- HTTPS через reverse proxy: Caddy, Nginx Proxy Manager, Traefik или nginx + certbot.

## 2. Создать Telegram Bot и Mini App

1. Откройте BotFather.
2. Создайте бота: `/newbot`.
3. Сохраните token в `TELEGRAM_BOT_TOKEN`.
4. Создайте Mini App для бота.
5. Укажите frontend HTTPS URL:

```text
https://app.tudasuda.tech
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
AUTH_TOKEN_TTL_HOURS=24
ADMIN_API_KEY=<long random admin key>
CORS_ORIGINS=https://app.tudasuda.tech
PUBLIC_APP_URL=https://app.tudasuda.tech
PUBLIC_API_URL=https://api.tudasuda.tech
VITE_API_URL=https://api.tudasuda.tech
VITE_APP_URL=https://app.tudasuda.tech
VITE_TONCONNECT_MANIFEST_URL=https://app.tudasuda.tech/tonconnect-manifest.json
VITE_ENABLE_MOCK_AUTH=false
```

Для TON testnet deposits:

```env
HOT_WALLET_ADDRESS=<hot wallet public address>
HOT_WALLET_MNEMONIC=<hot wallet mnemonic words>
HOT_WALLET_JETTON_TRANSFER_GAS_TON=0.08
# Deprecated: use HOT_WALLET_ADDRESS instead.
# PROJECT_TON_WALLET=
TONCENTER_API_KEY=<optional key>
```

Комиссии сервиса:

```env
PURCHASE_FEE_PERCENT=1
BUY_COMMISSION_PERCENT=1
TDSD_FIXED_PRICE_TON=0.1
TRANSFER_COMMISSION_PERCENT=10
TREASURY_WALLET_ADDRESS=<treasury wallet public address>
```

`TDSD_FIXED_PRICE_TON=0.1` задает фиксированную цену `1 TDSD = 0.1 TON`. `PURCHASE_FEE_PERCENT=1` удерживает 1% из gross-суммы TDSD перед финальным зачислением на внутренний баланс и перед on-chain выплатой с hot wallet. `BUY_COMMISSION_PERCENT` оставлен как совместимый alias. `TRANSFER_COMMISSION_PERCENT=10` удерживает 10% из суммы TDSD-дара: отправитель списывает полную сумму, получатель получает 90%, treasury получает 10%.

`HOT_WALLET_ADDRESS` отвечает за прием оплаты TON при покупке TDSD и за подпись on-chain выплаты TDSD пользователю. `PROJECT_TON_WALLET` больше не нужен и поддерживается только как временный fallback для старых серверных env, если `HOT_WALLET_ADDRESS` еще не задан.

Hot wallet должен совпадать с `HOT_WALLET_ADDRESS`, иметь запас TDSD и небольшой запас TON для gas. На сервере хранится только `HOT_WALLET_MNEMONIC`; treasury mnemonic не нужен и не должен храниться на сервере. Если `HOT_WALLET_MNEMONIC` не задан, покупка может быть подтверждена, но автоматическая выплата вернет пользователю сообщение `Автоматическая выплата временно недоступна`.

Для TDSD после deploy Jetton:

```env
TDSD_JETTON_MASTER_ADDRESS=<TDSD jetton master address>
TDSD_PROJECT_JETTON_WALLET=<Project Jetton Wallet>
TDSD_DEPOSITS_ENABLED=true
```

Пока контракт не развернут, оставьте:

```env
TDSD_DEPOSITS_ENABLED=false
```

В этом режиме покупка TDSD работает через фиксированную цену: пользователь выбирает сумму TDSD, оплачивает рассчитанную сумму TON через кошелек, а backend проверяет оплату по адресу проекта, сумме и комментарию.

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

Безопасная схема деплоя с сохранением работающих контейнеров на случай ошибки build:

```bash
git fetch origin
git reset --hard origin/main
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d
```

Не запускайте `docker compose down` перед build: если сборка упадет, старые контейнеры продолжат обслуживать сайт.

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
5. В профиле должно отображаться Telegram photo, если оно есть.
6. На профиле подключите кошелек.
7. Откройте покупку TDSD и проверьте курс `1 TDSD = 0.1 TON`.
8. Создайте покупку TDSD.
9. Оплатите через кошелек или вручную по показанному адресу проекта.
10. Нажмите “Проверить статус”.
11. Проверьте `AssetBalance` и `AssetLedgerEntry`.

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
TELEGRAM_BOT_USERNAME=tudasuda_tdsd_bot
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

Не передавайте `ADMIN_API_KEY` в frontend build. Admin API вызывается только backend-side или через защищенный backend-доступ с header `X-Admin-Token`.

## 11. Rollback

Если deploy не прошел:

```bash
docker compose logs backend --tail=200
docker compose down
```

Проверьте env validation error. Backend намеренно не стартует, если production env небезопасен.

## 12. Full E2E

Перед закрытым testnet launch пройдите полный сценарий из `E2E_TESTING.md`.
