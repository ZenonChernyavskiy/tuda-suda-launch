# End-to-End Testing Guide

Этот сценарий проверяет Tuda Suda перед закрытым testnet launch: backend,
frontend, Telegram Mini App, TON Connect, TON deposits, TDSD Jetton deposits,
internal asset gifts, ledger, karma, history и admin endpoints.

Продуктовая рамка: Tuda Suda - приложение про случайную цифровую щедрость и
репутацию. Проверки ниже не должны добавлять инвестиционные, casino,
play-to-earn или NFT-сценарии.

## 1. Clean Install

Проверьте, что в проекте нет локальных артефактов:

```bash
find . -name node_modules -o -name .venv -o -name dist -o -name __pycache__ -o -name .pytest_cache -o -name .DS_Store
```

Ожидаемо: команда не показывает файлов, которые должны попасть в репозиторий.

Backend:

```bash
cd tuda-suda/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py
python -m compileall app
uvicorn app.main:app --reload
```

Проверьте:

```text
http://localhost:8000/health
http://localhost:8000/ready
```

Frontend:

```bash
cd tuda-suda/frontend
npm install
cp .env.example .env
npm run build
npm run dev
```

Проверьте `http://localhost:5173`: белого экрана быть не должно.

## 2. Local MVP Flow

1. Откройте frontend в браузере.
2. Убедитесь, что development mock-login работает.
3. Проверьте главную:
   - пользователь создан;
   - баланс активов отображается;
   - karma/rank отображаются.
4. Создайте второго тестового пользователя через seed или mock user switch.
5. Отправьте internal asset gift.
6. Проверьте:
   - sender balance уменьшился;
   - receiver balance увеличился;
   - `AssetGift.status=completed`;
   - sender ledger содержит `gift_sent`;
   - receiver ledger содержит `gift_received`;
   - karma отправителя увеличилась;
   - history и leaderboard обновились.

## 3. Docker Compose Smoke Test

```bash
cd tuda-suda
cp .env.production.example .env.production
```

Для локальной Docker-проверки можно использовать тестовые HTTPS-домены через
reverse proxy или временно поднять dev-like env. Для production-like проверки
обязательно:

```env
APP_ENV=production
ALLOW_MOCK_AUTH=false
AUTO_INIT_DB=false
DATABASE_URL=postgresql+psycopg://tuda_suda:<password>@postgres:5432/tuda_suda
CORS_ORIGINS=https://app.tudasuda.tech
PUBLIC_APP_URL=https://app.tudasuda.tech
PUBLIC_API_URL=https://api.tudasuda.tech
```

Запуск:

```bash
docker compose --env-file .env.production up --build -d
docker compose ps
docker compose logs backend --tail=100
```

Проверьте:

```text
https://api.tudasuda.tech/health
https://api.tudasuda.tech/ready
https://app.tudasuda.tech
```

## 4. Telegram Mini App

1. Создайте Telegram bot через BotFather.
2. Создайте Mini App и укажите frontend HTTPS URL.
3. Настройте Menu Button.
4. В backend production env задайте:

```env
TELEGRAM_BOT_TOKEN=<bot token>
ALLOW_MOCK_AUTH=false
```

5. Откройте Mini App из Telegram.
6. Проверьте:
   - backend принимает реальный `initData`;
   - mock-login недоступен;
   - пользователь создается автоматически;
   - повторный вход возвращает того же пользователя.

## 5. TON Connect

1. Проверьте manifest:

```text
https://app.tudasuda.tech/tonconnect-manifest.json
```

2. В профиле нажмите “Подключить TON кошелек”.
3. Подключите testnet wallet.
4. Нажмите “Сохранить кошелек”.
5. Проверьте:
   - адрес отображается сокращенно;
   - `GET /wallet/me` возвращает адрес;
   - `wallet_connections` содержит запись;
   - кнопка disconnect очищает адрес.

## 6. TON Testnet Deposit

Backend env:

```env
TON_NETWORK=testnet
PROJECT_TON_WALLET=<project testnet TON wallet>
TONCENTER_API_KEY=<optional>
```

Проверка:

1. Создайте TON deposit во frontend.
2. Отправьте ровно указанную сумму testnet TON на project wallet.
3. Обязательно добавьте memo/comment из приложения.
4. Нажмите “Проверить статус”.
5. Проверьте:
   - deposit стал `confirmed`;
   - `AssetBalance` TON увеличился;
   - `AssetLedgerEntry.entry_type=deposit`;
   - legacy `User.ton_balance_nano` обновлен как mirror;
   - TON balance отображается во frontend.

Повторная проверка того же tx не должна начислить баланс второй раз.

## 7. TDSD Contract Testnet Deployment

```bash
cd tuda-suda/contracts
npm install
cp .env.contracts.example .env.contracts
```

Заполните:

```env
TDSD_METADATA_URL=https://app.tudasuda.tech/tdsd-metadata.json
TDSD_OWNER_ADDRESS=<admin wallet>
TDSD_PROJECT_WALLET_ADDRESS=<project owner wallet>
```

Сборка и тест:

```bash
npm run build
npm test
```

Деплой:

```bash
npm run deploy:testnet
```

Сохраните:

- Jetton Master address;
- Project Jetton Wallet address;
- wallet code hash;
- metadata URL/hash.

Проверка getters:

```env
TDSD_JETTON_MASTER_ADDRESS=<master>
TDSD_WALLET_OWNER=<project owner wallet>
```

```bash
npm run get:data
```

## 8. Connect TDSD To Backend

Backend env:

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

Apply:

```bash
cd tuda-suda/backend
alembic upgrade head
python production_seed.py
```

Проверьте:

```text
GET /ready
GET /assets
GET /assets/balances
```

Ожидаемо: TDSD активен, `provider_key=jetton`, `contract_address` совпадает с
Jetton Master.

## 9. TDSD Deposit Flow

1. Создайте TDSD deposit во frontend.
2. Через wallet отправьте TDSD с точным memo/comment.
3. Нажмите “Проверить статус”.
4. Проверьте:
   - `AssetDeposit.status=confirmed`;
   - `AssetBalance` TDSD увеличился;
   - `AssetLedgerEntry.entry_type=deposit`;
   - frontend показывает TDSD balance.

Если TON Center не вернул decoded Jetton transfer, deposit должен оставаться
retryable, а не начисляться ошибочно.

## 10. TDSD Internal Gift

1. У пользователя A должен быть TDSD balance.
2. Пользователь B должен существовать и быть активным.
3. Пользователь A выбирает TDSD и отправляет подарок случайному пользователю.
4. Проверьте:
   - невозможно отправить самому себе;
   - невозможно отправить больше баланса;
   - невозможно отправить inactive asset;
   - sender `AssetBalance` уменьшился на полную отправленную сумму;
   - receiver `AssetBalance` увеличился на сумму за вычетом комиссии;
   - treasury `AssetBalance` увеличился на комиссию;
   - `AssetGift` создан;
   - ledger содержит `gift_sent`, `gift_received`, `fee_transfer` и `treasury_income`;
   - общий список транзакций показывает дар и системную комиссию;
   - karma/rank/leaderboard/history обновились.

## 11. Admin Checks

Запросы должны содержать:

```text
X-Admin-Token: <ADMIN_API_KEY>
```

Проверьте:

- `GET /admin/assets`
- `GET /admin/users`
- `GET /admin/ledger/all`
- `GET /admin/transactions`
- `GET /admin/statistics`

Без admin token endpoints должны возвращать `403`.

## 12. Security Checks

Перед testnet launch:

- `.env`, seed phrases and private keys absent from repo;
- `ALLOW_MOCK_AUTH=false` in production;
- Telegram `initData` validation enabled;
- CORS contains only HTTPS frontend origin;
- admin API is token-protected;
- inactive assets cannot be used for deposits or gifts;
- negative balances cannot be created;
- duplicate tx hash cannot credit twice;
- logs do not print secrets;
- withdrawals are absent by design;
- mainnet is not enabled.

## 13. Testnet Launch Acceptance

Closed testnet launch is acceptable only when:

- clean install succeeds;
- Docker Compose starts backend, frontend and PostgreSQL;
- Telegram Mini App opens via HTTPS;
- TON Connect works;
- TON deposit works;
- TDSD contract builds/tests/deploys;
- TDSD deposit works;
- internal TON/TDSD gifts work;
- ledger/history/leaderboard/admin checks pass;
- backups, TLS renewals and monitoring are configured on the VPS.

Public production launch still requires external smart-contract audit and
operational monitoring.
