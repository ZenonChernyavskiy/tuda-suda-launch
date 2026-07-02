# Tuda Suda

Telegram Mini App про случайную цифровую щедрость: пользователь пополняет внутренний баланс актива, отправляет подарок случайному человеку, получает карму и формирует репутацию через прозрачный ledger.

Проект не является казино, биржей, банком, инвестиционной платформой или play-to-earn продуктом. Деньги и токены здесь только инструмент подарка; основная ценность - социальный жест, доверие, карма и репутация.

## Что реализовано

- React + Vite frontend для Telegram Mini App.
- FastAPI backend.
- SQLite для локальной разработки.
- PostgreSQL для production.
- Telegram WebApp initData auth.
- Локальный mock-login только для development.
- TON Connect.
- TON testnet deposits.
- Asset-based economy: `Asset`, `AssetBalance`, `AssetLedgerEntry`.
- Internal off-chain asset gifts через `AssetGift`.
- Provider layer: `ton_native` и `jetton`.
- TDSD Jetton asset support через `JettonProvider`.
- Admin API foundation.
- Alembic migrations.
- Docker и docker-compose.
- Production deployment docs.

Withdrawals, mainnet launch и реальные публичные финансовые сценарии не включены в MVP. Перед mainnet нужен внешний security audit.

## Структура

```text
tuda-suda/
  backend/
    app/
    alembic/
    Dockerfile
    requirements.txt
    seed.py
    production_seed.py
  frontend/
    src/
    public/tonconnect-manifest.json
    Dockerfile
  contracts/
    func/
    metadata/
    deploy/
  DEPLOYMENT.md
  PRODUCTION_CHECKLIST.md
  docker-compose.yml
  .env.example
  .env.production.example
```

## Local Development

Backend:

```bash
cd tuda-suda/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py
uvicorn app.main:app --reload
```

Frontend:

```bash
cd tuda-suda/frontend
npm install
cp .env.example .env
npm run dev
```

Откройте `http://localhost:5173`. В development включен mock mode, поэтому приложение можно проверить без Telegram.

## Production Deployment

Production запуск описан в [DEPLOYMENT.md](./DEPLOYMENT.md).

Коротко:

```bash
cp .env.production.example .env.production
# заполнить TELEGRAM_BOT_TOKEN, AUTH_TOKEN_SECRET, ADMIN_API_KEY, домены, CORS и TON/TDSD env
docker compose --env-file .env.production up --build -d
```

Backend в Docker выполняет:

```bash
alembic upgrade head
python production_seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

В production:

- `APP_ENV=production`
- `ALLOW_MOCK_AUTH=false`
- `AUTO_INIT_DB=false`
- `DATABASE_URL` должен указывать на PostgreSQL
- `CORS_ORIGINS` должен содержать только HTTPS-домены
- `VITE_API_URL`, `VITE_APP_URL`, `VITE_TONCONNECT_MANIFEST_URL` не должны указывать на localhost

## Telegram Setup

1. Создайте бота через BotFather.
2. Получите `TELEGRAM_BOT_TOKEN`.
3. Создайте Mini App через BotFather.
4. Укажите HTTPS URL frontend.
5. Настройте menu button на URL Mini App.
6. На backend задайте `TELEGRAM_BOT_TOKEN`.
7. Отключите mock auth: `ALLOW_MOCK_AUTH=false`.

Backend проверяет подпись Telegram `initData` и свежесть `auth_date`.

## TON Connect Setup

Frontend использует `@tonconnect/ui-react`.

Manifest лежит здесь:

```text
frontend/public/tonconnect-manifest.json
```

Перед deploy замените:

```json
{
  "url": "https://app.tudasuda.tech",
  "name": "Tuda-Suda",
  "iconUrl": "https://app.tudasuda.tech/tonconnect-icon.svg"
}
```

на реальные значения вашего домена.

В frontend env:

```env
VITE_TONCONNECT_MANIFEST_URL=https://app.tudasuda.tech/tonconnect-manifest.json
```

В браузерный bundle не добавлены `Buffer`, `process` или `global` polyfills. Frontend не импортирует `@ton/core` напрямую.

## TDSD Setup

TDSD - собственный Jetton-токен проекта. Он нужен для внутренней экономики подарков и репутации, а не для обещаний заработка.

Contract package лежит в:

```text
contracts/
```

Contract workspace содержит Blueprint-compatible scripts:

```bash
cd contracts
npm install
npm run build
npm test
npm run deploy:testnet
npm run mint:testnet
npm run transfer:testnet
npm run burn:testnet
npm run get:data
```

Testnet deployment checklist:

```text
contracts/deploy/TESTNET_DEPLOYMENT.md
```

После деплоя Jetton Master настройте backend:

```env
SEED_TDSD_ASSET=true
TDSD_ASSET_SYMBOL=TDSD
TDSD_ASSET_NAME=Tuda Suda Token
TDSD_DECIMALS=9
TDSD_NETWORK=ton_testnet
TDSD_JETTON_MASTER_ADDRESS=<Jetton Master>
TDSD_PROJECT_JETTON_WALLET=<Project Jetton Wallet>
TDSD_DEPOSITS_ENABLED=true
```

Затем:

```bash
cd backend
alembic upgrade head
python production_seed.py
```

Если `TDSD_JETTON_MASTER_ADDRESS` пустой, seed создает TDSD как неактивный asset. Если адрес задан, TDSD становится активным и появляется во frontend в балансах, gifts и deposits.

## Service Fees

Комиссии вынесены в env и считаются backend-сервисом `fee_service.py`.

```env
BUY_COMMISSION_PERCENT=1
TRANSFER_COMMISSION_PERCENT=10
TREASURY_WALLET_ADDRESS=UQAOgQnt-ZMtAsMWtnL9zFs1Id27b8L3gc35pvQZA4dmUZg6
HOT_WALLET_ADDRESS=UQB-gyjeCOixVUyVx-X_4FqhXeOwjCIUYnkue4vQESUx6f66
TDSD_JETTON_MASTER_ADDRESS=EQBZkfdol6WOj-GXByKLeRlo70ktYIQnTA5Hq_gT6KVYvY3n
```

Для TDSD-покупки комиссия платформы составляет `BUY_COMMISSION_PERCENT`. Если пользователь покупает 1000 TDSD, на его внутренний баланс в итоге попадет 990 TDSD, а 10 TDSD будут отражены как комиссия платформы и treasury income.

Для TDSD-подарка отправитель списывает полную сумму, получатель получает сумму за вычетом `TRANSFER_COMMISSION_PERCENT`, а treasury получает комиссию во внутреннем `AssetBalance`. Если отправитель дарит 100 TDSD, отправитель списывает 100 TDSD, получатель получает 90 TDSD, treasury получает 10 TDSD. Ledger фиксирует `gift_sent`, `gift_received`, `fee_transfer` и `treasury_income`.

Quote endpoints:

- `GET /fees/config`
- `POST /fees/purchase/quote`
- `POST /fees/transfer/quote`

TDSD deposit flow используется как покупка/пополнение внутреннего TDSD-баланса: после подтверждения deposit backend удерживает 1% комиссии и возвращает финальный баланс пользователя.

Важно: полноценный on-chain Jetton transfer из frontend через TON Connect с двумя Jetton transfer payload сообщениями пока не включен в браузерный код. Текущий gift flow остается внутренней off-chain операцией с ledger-аудитом, чтобы не возвращать `Buffer`/Node-only зависимости в Vite bundle.

## Database

Local:

```env
DATABASE_URL=sqlite:///./tuda_suda.db
AUTO_INIT_DB=true
```

Production:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/tuda_suda
AUTO_INIT_DB=false
```

Миграции:

```bash
cd backend
alembic upgrade head
```

Alembic migration `202606270001_stage8_initial_schema.py` создает:

- users
- assets
- wallet_connections
- asset_balances
- asset_deposits
- ton_deposits
- asset_gifts
- asset_ledger_entries
- transactions
- reputation_events

## Environment Variables

Главные backend переменные:

- `APP_ENV`
- `DATABASE_URL`
- `TELEGRAM_BOT_TOKEN`
- `ALLOW_MOCK_AUTH`
- `AUTH_TOKEN_SECRET`
- `ADMIN_API_KEY`
- `CORS_ORIGINS`
- `PUBLIC_APP_URL`
- `PUBLIC_API_URL`
- `PROJECT_TON_WALLET`
- `HOT_WALLET_ADDRESS`
- `TREASURY_WALLET_ADDRESS`
- `BUY_COMMISSION_PERCENT`
- `TRANSFER_COMMISSION_PERCENT`
- `TONCENTER_API_KEY`
- `TDSD_JETTON_MASTER_ADDRESS`
- `TDSD_PROJECT_JETTON_WALLET`
- `TDSD_DEPOSITS_ENABLED`

Главные frontend переменные:

- `VITE_API_URL`
- `VITE_APP_URL`
- `VITE_TONCONNECT_MANIFEST_URL`
- `VITE_ENABLE_MOCK_AUTH`
- `VITE_ENABLE_ADMIN`

Смотрите полный список в `.env.example` и `.env.production.example`.

## API

Public:

- `GET /health`
- `GET /ready`
- `GET /readiness`
- `POST /auth/telegram`
- `GET /me`
- `POST /gift/send`
- `GET /transactions`
- `GET /leaderboard`
- `GET /fees/config`
- `POST /fees/purchase/quote`
- `POST /fees/transfer/quote`
- `GET /referrals/me`
- `POST /wallet/connect`
- `GET /wallet/me`
- `DELETE /wallet/disconnect`
- `GET /assets`
- `GET /assets/balances`
- `GET /assets/ledger`
- `GET /assets/{symbol}/balance`
- `POST /asset-deposits/create`
- `POST /asset-deposits/{deposit_id}/verify`
- `GET /asset-deposits`
- `POST /asset-gifts/send`
- `POST /asset-gifts/send-random`
- `GET /asset-gifts`
- `GET /asset-gifts/feed`
- `GET /asset-gifts/leaderboard`

Admin, требует `X-Admin-Token`:

- `GET /admin/assets`
- `POST /admin/assets/create`
- `GET /admin/ledger/all`
- `GET /ledger/all`
- `GET /admin/users`
- `GET /admin/transactions`
- `GET /admin/reputation`
- `GET /admin/karma`
- `GET /admin/statistics`

## Ledger

Все asset-операции записываются в `AssetLedgerEntry`:

- `deposit`
- `gift_sent`
- `gift_received`
- `adjustment`
- `fee`
- `fee_purchase`
- `fee_transfer`
- `treasury_income`
- `referral_reward`
- `referral_reward_pending`
- `referral_reward_credit`

Баланс хранится только в smallest units:

- TON: nanotons
- TDSD: smallest units по `decimals`

Float не используется для расчетов балансов.

## Referral Program

Реферальная программа одноуровневая и не начисляет награды за регистрацию,
подарки или обычные переводы. Пригласивший фиксируется один раз при первом
входе приглашенного пользователя через Telegram referral-ссылку.

Backend строит ссылку из env:

```env
REFERRALS_ENABLED=true
REFERRAL_REWARD_PERCENT=10
REFERRAL_REWARD_ASSET_SYMBOL=TDSD
TELEGRAM_BOT_USERNAME=rudasuda_tdsd_bot
TELEGRAM_MINI_APP_SHORT_NAME=
FRONTEND_URL=https://app.tudasuda.tech
```

Если `TELEGRAM_MINI_APP_SHORT_NAME` пустой, ссылка имеет вид:

```text
https://t.me/rudasuda_tdsd_bot?start=ref_<REFERRAL_CODE>
```

Если short name задан:

```text
https://t.me/rudasuda_tdsd_bot/<TELEGRAM_MINI_APP_SHORT_NAME>?startapp=ref_<REFERRAL_CODE>
```

В текущей backend-архитектуре награда начисляется после успешного подтверждения
TDSD `AssetDeposit`, потому что именно этот шаг зачисляет TDSD на внутренний
баланс. Награда составляет `REFERRAL_REWARD_PERCENT` от суммы TDSD-депозита,
создает запись `ReferralReward` и ledger entry `referral_reward_credit`.
Повторное начисление за один deposit блокируется через `purchase_id`.

## Security

Production validation при старте backend проверяет:

- PostgreSQL вместо SQLite
- mock auth выключен
- Telegram token задан
- auth secret заменен
- admin key задан
- CORS только явные HTTPS origins
- public URLs используют HTTPS
- TDSD env заполнены, если deposits enabled

Mock endpoints и mock auth не должны использоваться в production.

## Roadmap

До публичного v1.0:

1. Прогнать внешний audit TDSD contracts.
2. Завершить testnet deployment и верификацию Jetton standard getters.
3. Провести нагрузочный тест ledger и gift flow.
4. Добавить полноценный admin UI поверх текущих admin endpoints.
5. Настроить monitoring, backups и alerting.
6. Провести legal/product review формулировок, чтобы не создавать ожиданий заработка.

## Full E2E

Полный сценарий проверки перед закрытым testnet launch описан в
[E2E_TESTING.md](./E2E_TESTING.md).
