# Production Checklist

## Product Philosophy

- [ ] Тексты не обещают заработок.
- [ ] Продукт не выглядит как казино, биржа или инвестиционная платформа.
- [ ] Основной сценарий остается “подарить случайному человеку”.
- [ ] Karma и reputation описаны как социальная репутация, а не финансовая выгода.

## Backend

- [ ] `APP_ENV=production`.
- [ ] `ALLOW_MOCK_AUTH=false`.
- [ ] `AUTO_INIT_DB=false`.
- [ ] `DATABASE_URL` указывает на PostgreSQL.
- [ ] `TELEGRAM_BOT_TOKEN` задан.
- [ ] `AUTH_TOKEN_SECRET` заменен на длинный секрет.
- [ ] `ADMIN_API_KEY` задан.
- [ ] `CORS_ORIGINS` содержит только HTTPS frontend domain.
- [ ] `PUBLIC_APP_URL` и `PUBLIC_API_URL` используют HTTPS.
- [ ] `alembic upgrade head` проходит успешно.
- [ ] `python production_seed.py` создает TON и TDSD assets.
- [ ] `GET /health` возвращает `ok`.
- [ ] `GET /ready` возвращает `ready`.
- [ ] `BUY_COMMISSION_PERCENT=1`.
- [ ] `TRANSFER_COMMISSION_PERCENT=10`.
- [ ] `TREASURY_WALLET_ADDRESS` задан и не берется с frontend.
- [ ] `HOT_WALLET_ADDRESS` задан.
- [ ] `GET /fees/config` возвращает production fee config.

## Frontend

- [ ] `VITE_API_URL` указывает на HTTPS backend.
- [ ] `VITE_APP_URL` указывает на HTTPS frontend.
- [ ] `VITE_TONCONNECT_MANIFEST_URL` указывает на HTTPS manifest.
- [ ] `VITE_ENABLE_MOCK_AUTH=false`.
- [ ] `VITE_ENABLE_ADMIN=false`.
- [ ] `npm run build` проходит.
- [ ] В production bundle нет прямого импорта `@ton/core`.
- [ ] Белого экрана нет.

## Telegram

- [ ] BotFather bot создан.
- [ ] Mini App создан.
- [ ] Menu Button настроен.
- [ ] Mini App открывается внутри Telegram.
- [ ] Backend принимает и проверяет `initData`.
- [ ] Mock-login в production недоступен.

## TON Connect

- [ ] `tonconnect-manifest.json` доступен по HTTPS.
- [ ] `url` в manifest указывает на production frontend.
- [ ] `iconUrl` доступен по HTTPS.
- [ ] Wallet подключается.
- [ ] Wallet сохраняется в backend.
- [ ] Wallet отключается.

## TON Deposits

- [ ] `HOT_WALLET_ADDRESS` задан.
- [ ] Hot wallet доступен и имеет TON для gas.
- [ ] Депозит создается.
- [ ] Memo/comment виден пользователю.
- [ ] Проверка депозита подтверждает только корректную transaction.
- [ ] `AssetBalance` увеличивается.
- [ ] `AssetLedgerEntry` создается.

## TDSD

- [ ] `cd contracts && npm install` проходит.
- [ ] `cd contracts && npm run build` проходит.
- [ ] `cd contracts && npm test` проходит.
- [ ] `contracts/.env.contracts` создан локально и не закоммичен.
- [ ] Jetton Master развернут в testnet.
- [ ] Project Jetton Wallet получен.
- [ ] `npm run get:data` подтверждает getters и wallet code hash.
- [ ] `TDSD_JETTON_MASTER_ADDRESS` задан.
- [ ] `TDSD_PROJECT_JETTON_WALLET` задан.
- [ ] `TDSD_DEPOSITS_ENABLED=true` только после testnet verification.
- [ ] TDSD asset активен в `GET /assets`.
- [ ] TDSD deposit проверяется.
- [ ] TDSD internal gift работает.
- [ ] TDSD gift списывает полную сумму, начисляет получателю net amount и создает `fee_transfer` + `treasury_income`.
- [ ] Контракты прошли внешний audit перед mainnet.

## Admin

- [ ] Admin API закрыт `X-Admin-Token`.
- [ ] Публичный frontend не показывает admin вкладки.
- [ ] Admin endpoints фильтруют users, ledger, transactions, reputation.

## Security

- [ ] Секреты не закоммичены.
- [ ] `.env` не попадает в Docker image.
- [ ] PostgreSQL password заменен.
- [ ] CORS не содержит wildcard.
- [ ] Ledger нельзя изменять через публичный API.
- [ ] Невозможно отправить 0, отрицательную сумму или сумму меньше/равную комиссии.
- [ ] Treasury wallet нельзя подменить через frontend payload.
- [ ] Withdrawals отсутствуют.
- [ ] Mainnet отключен до отдельного security этапа.

## Operations

- [ ] Настроены backups PostgreSQL.
- [ ] Настроены logs.
- [ ] Настроен uptime monitoring.
- [ ] Настроены TLS certificates renewals.
- [ ] Есть rollback plan.

## End-to-End

- [ ] Пройден полный сценарий из `E2E_TESTING.md`.
- [ ] Результаты testnet запуска сохранены в launch notes.
