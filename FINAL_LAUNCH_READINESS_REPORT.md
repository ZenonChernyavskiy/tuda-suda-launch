# Final Launch Readiness Report

Дата: 2026-06-27

Проект: Tuda Suda Telegram Mini App.

Цель работы: закрыть проблемы из `stage_x_launch_audit.md`, очистить проект от локальных артефактов, подготовить backend/frontend/Docker/docs/contracts к реальному testnet запуску и честно оценить готовность к production.

## 1. Итоговый статус

Проект доведен до состояния, пригодного для закрытого интернет-testnet запуска после чистой установки зависимостей, настройки env, деплоя TDSD Jetton в TON Testnet и прохождения полного E2E сценария.

Проект пока не готов к публичному mainnet production launch, потому что для этого все еще обязательны:

- внешний аудит TDSD smart contracts;
- реальный testnet deploy и подтвержденный E2E на TON Testnet;
- production monitoring, backups, alerting и TLS renewal checks;
- security review инфраструктуры и admin-доступов;
- legal/product review текстов перед публичной аудиторией.

Философия продукта сохранена: Tuda Suda остается Mini App про случайную цифровую щедрость, карму, репутацию и прозрачный ledger. Новые игровые, casino, NFT, Battle Pass, collection или investment-механики не добавлялись.

## 2. Главные исправления

- Удалены локальные артефакты: `.venv`, `node_modules`, `dist`, `.DS_Store`, `__pycache__`, локальные `.env`, локальная SQLite DB и кеши.
- Расширен `.gitignore`, чтобы секреты, build artifacts, кеши, локальные базы и contract artifacts не попадали в Git.
- Расширены backend/frontend `.dockerignore`, чтобы `.env`, базы, кеши и сборки не попадали в Docker build context.
- Добавлен полноценный contract workspace для TDSD:
  - `package.json`
  - `tsconfig.json`
  - Blueprint config
  - wrappers
  - compile targets
  - deploy/mint/transfer/burn/getter scripts
  - sandbox tests
  - `.env.contracts.example`
- Исправлена загрузка contract env: scripts читают `.env.contracts`.
- Добавлен публичный frontend metadata file: `frontend/public/tdsd-metadata.json`.
- Усилен backend readiness: если `TDSD_DEPOSITS_ENABLED=true`, `/ready` проверяет активный TDSD asset, provider `jetton`, contract address и project Jetton wallet.
- Усилена startup validation: TON/TDSD адреса проверяются на разумный TON-формат при старте.
- Обновлена документация:
  - `README.md`
  - `DEPLOYMENT.md`
  - `PRODUCTION_CHECKLIST.md`
  - `contracts/README.md`
  - `contracts/deploy/TESTNET_DEPLOYMENT.md`
  - добавлен `E2E_TESTING.md`

## 3. Измененные и добавленные файлы

Основные измененные файлы:

- `.gitignore`
- `README.md`
- `DEPLOYMENT.md`
- `PRODUCTION_CHECKLIST.md`
- `backend/.dockerignore`
- `backend/app/config.py`
- `backend/app/main.py`
- `frontend/.dockerignore`
- `contracts/README.md`
- `contracts/deploy/TESTNET_DEPLOYMENT.md`
- `contracts/scripts/env.ts`
- `contracts/wrappers/TdsdJettonMaster.ts`
- `contracts/wrappers/TdsdJettonWallet.ts`

Основные новые файлы:

- `E2E_TESTING.md`
- `FINAL_LAUNCH_READINESS_REPORT.md`
- `frontend/public/tdsd-metadata.json`
- `contracts/package.json`
- `contracts/tsconfig.json`
- `contracts/.env.contracts.example`
- `contracts/blueprint.config.ts`
- `contracts/compilables/TdsdJettonMaster.compile.ts`
- `contracts/compilables/TdsdJettonWallet.compile.ts`
- `contracts/scripts/deployTdsd.ts`
- `contracts/scripts/mintTdsd.ts`
- `contracts/scripts/transferTdsd.ts`
- `contracts/scripts/burnTdsd.ts`
- `contracts/scripts/getTdsdData.ts`
- `contracts/tests/TdsdJetton.spec.ts`

Удаленные локальные артефакты:

- `backend/.venv`
- `backend/.env`
- `backend/tuda_suda.db`
- `frontend/node_modules`
- `frontend/dist`
- `frontend/.npm-cache`
- `frontend/.env`
- `.DS_Store`
- `__pycache__`
- `.vscode`

## 4. Локальный запуск после очистки

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

Проверить:

```text
http://localhost:8000/health
http://localhost:8000/ready
http://localhost:5173
```

## 5. Docker запуск

```bash
cd tuda-suda
cp .env.production.example .env.production
```

Заполнить production env:

- `TELEGRAM_BOT_TOKEN`
- `AUTH_TOKEN_SECRET`
- `ADMIN_API_KEY`
- `POSTGRES_PASSWORD`
- `CORS_ORIGINS`
- `PUBLIC_APP_URL`
- `PUBLIC_API_URL`
- `VITE_API_URL`
- `VITE_APP_URL`
- `VITE_TONCONNECT_MANIFEST_URL`
- TON/TDSD env после готовности testnet.

Запуск:

```bash
docker compose --env-file .env.production up --build -d
```

Backend container выполняет:

```bash
alembic upgrade head
python production_seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Проверить:

```bash
docker compose ps
docker compose logs backend --tail=100
```

## 6. VPS deploy

Минимальный production путь:

1. Поднять VPS с Ubuntu 22.04/24.04.
2. Установить Docker и Docker Compose plugin.
3. Настроить DNS:
   - `app.tudasuda.tech` на frontend;
   - `api.tudasuda.tech` на backend.
4. Настроить HTTPS reverse proxy:
   - Caddy, Traefik, Nginx Proxy Manager или nginx + certbot.
5. Заполнить `.env.production`.
6. Запустить Docker Compose.
7. Проверить:
   - `https://api.tudasuda.tech/health`
   - `https://api.tudasuda.tech/ready`
   - `https://app.tudasuda.tech`
   - `https://app.tudasuda.tech/tonconnect-manifest.json`
   - `https://app.tudasuda.tech/tdsd-metadata.json`

Подробный путь описан в `DEPLOYMENT.md`.

## 7. Telegram Mini App

1. Создать бота через BotFather.
2. Создать Mini App.
3. Указать frontend HTTPS URL.
4. Настроить menu button.
5. В backend production env задать:

```env
APP_ENV=production
ALLOW_MOCK_AUTH=false
TELEGRAM_BOT_TOKEN=<bot token>
```

6. Проверить вход из Telegram:
   - есть `initData`;
   - backend проверяет подпись;
   - mock-login недоступен;
   - повторный вход возвращает того же пользователя.

## 8. TON Connect

Frontend env:

```env
VITE_TONCONNECT_MANIFEST_URL=https://app.tudasuda.tech/tonconnect-manifest.json
```

Manifest:

```text
frontend/public/tonconnect-manifest.json
```

Перед deploy нужно заменить placeholder домены на реальные.

Важно: frontend не импортирует `@ton/core`, не требует `Buffer`, `process` или `global` polyfills. TDSD contract tooling отделен в `contracts/` и работает только в Node/Blueprint окружении.

## 9. TDSD Jetton deploy

Contract workspace:

```bash
cd tuda-suda/contracts
npm install
cp .env.contracts.example .env.contracts
```

Заполнить:

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

После деплоя:

```env
TDSD_JETTON_MASTER_ADDRESS=<master>
TDSD_WALLET_OWNER=<project owner wallet>
```

```bash
npm run get:data
```

Mint:

```env
TDSD_MINT_RECIPIENT=<recipient owner wallet>
TDSD_MINT_AMOUNT_UNITS=100000000000
```

```bash
npm run mint:testnet
```

Burn/transfer scripts также подготовлены:

```bash
npm run transfer:testnet
npm run burn:testnet
```

Приватные ключи и seed-фразы не должны храниться в репозитории или `.env.contracts`.

## 10. Подключение TDSD к backend

После testnet deploy:

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
cd tuda-suda/backend
alembic upgrade head
python production_seed.py
```

Проверить:

```text
GET /ready
GET /assets
GET /assets/balances
```

Ожидаемо: TDSD активен, `provider_key=jetton`, `contract_address` совпадает с Jetton Master.

## 11. E2E сценарий

Полный пошаговый сценарий находится в:

```text
E2E_TESTING.md
```

Он покрывает:

- clean install;
- local MVP flow;
- Docker smoke;
- Telegram Mini App auth;
- TON Connect;
- TON testnet deposit;
- TDSD contract deploy;
- TDSD backend activation;
- TDSD deposit;
- internal TON/TDSD gifts;
- ledger/history/karma/leaderboard;
- admin endpoints;
- security checks.

## 12. Security audit summary

Проверено и усилено:

- `.env`, local DB, venv, node_modules, dist и кеши удалены.
- `.gitignore` блокирует секреты, seed/mnemonic/private key files, локальные env, contract build artifacts.
- `.dockerignore` не отправляет локальные env/db/cache в Docker build context.
- Production validation блокирует SQLite, mock auth, wildcard/local CORS и пустые secrets.
- Telegram auth требует `initData` в production.
- Admin API закрыт `X-Admin-Token`.
- `/ready` проверяет TDSD readiness, если Jetton deposits включены.
- Frontend production build не включает прямой `@ton/core`.
- Ledger остается backend-controlled; публичных endpoints для ручного изменения ledger нет.
- Internal gifts не позволяют отправлять самому себе или уходить в отрицательный баланс.
- Inactive assets не должны использоваться для deposits/gifts.
- Withdrawals отсутствуют по архитектурному решению текущего этапа.

Остается до public launch:

- внешний smart-contract audit;
- инфраструктурный pentest;
- проверка TON Center decoded Jetton transfer на реальных testnet транзакциях;
- мониторинг, backup policy, alerting;
- полноценная admin role model вместо одного `X-Admin-Token`;
- rate limiting на публичных endpoints.

## 13. Выполненные проверки в Codex

Успешно:

- `python -m compileall backend/app backend/production_seed.py backend/seed.py`
- direct backend health/readiness function calls:
  - `/health`: `ok`
  - `/ready`: `ready`
- `npm install` в `frontend`
- `npm run build` в `frontend`
- frontend scan: нет прямого `@ton/core`, `Buffer`, `process`, `global` в source/config
- secret scan по репозиторию без `node_modules/dist/.venv`: подозрительных секретов не найдено
- cleanup verification: не осталось `.venv`, `node_modules`, `dist`, `.env`, `.DS_Store`, `__pycache__`, локальных DB

Ограничения среды Codex:

- `pip install -r requirements.txt` не смог скачать Alembic из-за DNS/network restriction к PyPI.
- Contract `npm install` не завершился из-за сетевого ограничения; поэтому `blueprint build/test` нельзя было выполнить здесь.
- `npm run dev` не смог открыть порт из-за `listen EPERM` в sandbox.
- FastAPI `TestClient` не запустился в старом локальном venv из-за отсутствующего `httpx2`; после clean install dev/test dependencies нужно проверить отдельно.

Эти ограничения не являются ошибками кода, но обязательны к проверке локально, на CI или VPS.

## 14. Testnet launch readiness

Готовность к закрытому Testnet Launch: условно готов после внешних проверок установки.

Можно переходить к testnet, когда выполнено:

- clean backend install проходит;
- clean frontend install/build проходит;
- contract `npm install`, `npm run build`, `npm test` проходят;
- TDSD Jetton Master развернут в TON Testnet;
- getters проверены;
- backend env заполнен реальными contract addresses;
- Docker Compose стартует на VPS;
- Telegram Mini App открывается по HTTPS;
- TON/TDSD deposits подтверждаются;
- internal gifts, ledger, history, karma and leaderboard работают в E2E.

## 15. Public production readiness

Готовность к публичному Production/Mainnet Launch: еще не готов.

Причины:

- нет внешнего аудита smart contracts;
- нет подтвержденного real-chain E2E в TON Testnet;
- нет production monitoring/backups/alerting в репозитории;
- admin model пока foundation-level;
- mainnet env и операционные процедуры должны быть утверждены отдельно;
- юридические и продуктовые формулировки нужно проверить перед публичным запуском.

Рекомендация: сначала провести закрытый testnet launch, собрать результаты E2E, исправить найденные chain/provider/infrastructure проблемы, затем заказать внешний audit TDSD contracts и только после этого планировать public v1.0/mainnet.
