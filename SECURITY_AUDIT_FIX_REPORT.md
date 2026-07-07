# SECURITY_AUDIT_FIX_REPORT

## Что изменено

Изменены файлы:

- `.env.example`
- `.env.production.example`
- `.gitignore`
- `README.md`
- `DEPLOYMENT.md`
- `PRODUCTION_CHECKLIST.md`
- `docker-compose.yml`
- `backend/app/config.py`
- `backend/app/hot_wallet_payout.py`
- `backend/app/main.py`
- `backend/app/ton_service.py`
- `frontend/Dockerfile`
- `frontend/.env.example`
- `frontend/src/api.js`
- `frontend/src/App.jsx`

## Frontend admin secret

`VITE_ADMIN_API_KEY` полностью убран из frontend:

- удален из `frontend/src/api.js`;
- удален из `frontend/Dockerfile`;
- удален из `docker-compose.yml`;
- удален из `frontend/.env.example`;
- удалены frontend admin API calls `getAdminAssets()` и `getGlobalLedger()`.

Frontend больше не добавляет `X-Admin-Token` и не содержит admin secret в JS bundle.

Admin endpoints остаются backend-only и требуют `X-Admin-Token` на backend.

## Safe defaults

Backend defaults ужесточены:

- `ALLOW_MOCK_AUTH=false`;
- `APP_ENV=production` по умолчанию;
- `AUTH_TOKEN_SECRET` больше не имеет dev-secret default;
- `AUTH_TOKEN_TTL_HOURS=24`;
- real wallet address defaults убраны из config.

Если `APP_ENV=production`, backend падает на старте при небезопасных значениях:

- пустой или placeholder `TELEGRAM_BOT_TOKEN`;
- пустой, короткий или placeholder `AUTH_TOKEN_SECRET`;
- пустой, короткий или placeholder `ADMIN_API_KEY`;
- пустой или placeholder `HOT_WALLET_MNEMONIC`;
- `DATABASE_URL` с `change-me`;
- sqlite database;
- wildcard/local/non-HTTPS CORS;
- отсутствующий `TDSD_JETTON_MASTER_ADDRESS`.

## Docker hardening

В `docker-compose.yml`:

- backend port закрыт на localhost: `127.0.0.1:8000:8000`;
- `POSTGRES_PASSWORD` больше не имеет `change-me` default и должен быть задан явно;
- frontend build args больше не принимают admin secret.

## Env examples

В `.env.example` и `.env.production.example`:

- реальные wallet addresses заменены на placeholders;
- `AUTH_TOKEN_TTL_HOURS=24`;
- `VITE_ADMIN_API_KEY` и `VITE_ENABLE_ADMIN` удалены;
- `POSTGRES_PASSWORD=change-me` заменен на placeholder.

## Logging hardening

Снижена детализация production logs:

- Toncenter `runGetMethod` больше не логирует полный response payload;
- hot wallet payout больше не логирует полный Toncenter result;
- wallet info response логируется только как набор keys;
- sendBoc result логируется summary-only;
- BOC/payload/private key/seed/mnemonic не логируются.

## Repo/archive hygiene

Обновлен `.gitignore`:

- `.git/`
- `.DS_Store`
- `__MACOSX/`
- `__pycache__/`
- `*.pyc`
- `*.pyo`
- `*.pyd`

Из рабочей папки удалены найденные `.DS_Store`, `__pycache__` и `*.pyc` вне `.git`.

Рабочая `.git` директория репозитория не удалялась.

## Duplicate checks

Проверены указанные места:

- `sync_legacy_ton_balance_units` — одна актуальная функция;
- `serialize_asset_gift_feed_item` — одна актуальная функция;
- `TransferFeeQuoteResponse.fee_amount_units` — дублирующего поля в схеме не найдено.

Дополнительно сохранена совместимость API fee quote: поле `fee_amount_units` не удалялось, чтобы не ломать существующий frontend/backend contract.

## Reveal logic

Reveal hardening:

- разрешены только допустимые context types;
- `context_id` должен быть каноническим для пары `context_type + target_role`;
- нельзя раскрыть произвольного пользователя по одному user id без валидного context;
- повторное раскрытие одной записи для того же viewer не списывает TDSD повторно.

## Проверки

Выполнено:

- backend syntax-check без записи `.pyc`;
- `npm run build` для frontend;
- проверка frontend bundle на отсутствие `VITE_ADMIN_API_KEY`, `VITE_ENABLE_ADMIN`, `X-Admin-Token`;
- `git diff --check`;
- проверка отсутствия `.DS_Store`, `__MACOSX`, `__pycache__`, `*.pyc` вне `.git`.

Не выполнено локально:

- `docker compose config`;
- `docker compose up`;
- `/health`.

Причина: в текущем окружении недоступна команда `docker`.
