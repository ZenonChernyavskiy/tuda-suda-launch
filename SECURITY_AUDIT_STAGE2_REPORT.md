# SECURITY_AUDIT_STAGE2_REPORT

## Измененные файлы

- `.dockerignore`
- `backend/.dockerignore`
- `frontend/.dockerignore`
- `backend/.env.example`
- `backend/app/asset_gift_service.py`
- `backend/app/main.py`
- `ARCHITECTURE_TDSD_BALANCE.md`
- `SECURITY_AUDIT_STAGE2_REPORT.md`

## Cleanup / Archive Hardening

Добавлен корневой `.dockerignore`, а backend/frontend `.dockerignore` расширены исключениями:

- `.git`
- `.DS_Store`
- `__MACOSX`
- `node_modules`
- `__pycache__`
- `*.pyc`

Рабочая `.git` директория не удалялась, потому что это история текущего репозитория. Для архивов и Docker build contexts она исключена.

Локальные артефакты, найденные в рабочей папке, удаляются после проверок: `.DS_Store` и `frontend/node_modules`.

## backend/.env.example

`backend/.env.example` помечен как development-only.

Из него убраны реальные адреса кошельков. Теперь используются placeholders:

- `HOT_WALLET_ADDRESS=<hot_wallet_public_address>`
- `TREASURY_WALLET_ADDRESS=<treasury_wallet_public_address>`
- `TDSD_JETTON_MASTER_ADDRESS=<tdsd_jetton_master_address>`

Также выставлено:

- `AUTH_TOKEN_TTL_HOURS=24`
- `ALLOW_MOCK_AUTH=false`

## Atomic TDSD Debit

Списание `AssetBalance` переведено на атомарный `UPDATE ... WHERE balance_units >= amount`.

Это применяется к:

- отправке asset gift через общий `debit_asset_balance`;
- раскрытию пользователя за 10 TDSD;
- всем будущим списаниям, которые используют общий helper `debit_asset_balance`.

Legacy `/gift/send`, который использует `users.balance`, тоже переведен на атомарный `UPDATE ... WHERE balance >= amount`, чтобы не оставлять аналогичную гонку в старом сценарии подарков.

## TDSD Balance Model

Добавлен `ARCHITECTURE_TDSD_BALANCE.md`.

Текущая модель зафиксирована так:

- `asset_balances` — in-app ledger для действий внутри приложения;
- on-chain доставка TDSD отслеживается отдельно через payout fields в `asset_deposits`;
- app balance нельзя описывать как гарантированный on-chain balance без успешного payout и reconciliation.

## Public Feed Privacy

Публичная лента больше не возвращает `comment` для `treasury_income`.

Это закрывает утечку служебных строк вида purchase/reveal ids из `asset_ledger_entries.comment`.

Admin ledger response не менялся: служебные комментарии остаются доступны только через admin API.

## Rate Limit

Добавлен in-memory rate limit:

- `/auth/telegram` — по IP;
- `/asset-deposits/{deposit_id}/verify` — по пользователю;
- `/ton/deposits/{deposit_id}/verify` — по пользователю;
- `/users/reveal` — по пользователю;
- `/asset-gifts/send` и `/asset-gifts/send-random` — по пользователю;
- legacy `/gift/send` — по пользователю.

Тексты ошибок пользовательские: `Слишком много запросов. Попробуйте позже.`

Для multi-instance production лучше перенести счетчики rate limit в Redis или другой общий storage.

## Проверки

Выполнено:

- backend syntax check без создания `__pycache__`: ok;
- frontend build: ok;
- env examples scan на реальные wallet addresses: ok;
- frontend scan на `VITE_ADMIN_API_KEY` / `X-Admin-Token`: ok.

Не выполнено локально:

- `docker compose config --quiet`, потому что Docker CLI не установлен в текущем окружении.

## Проверка после деплоя

1. Убедиться, что production env содержит реальные значения только на сервере, не в examples.
2. Проверить `/health`.
3. Проверить auth и убедиться, что частые повторные запросы получают 429.
4. Проверить покупку/пополнение TDSD.
5. Проверить отправку asset gift при недостаточном балансе.
6. Проверить раскрытие пользователя при недостаточном балансе и при повторном тапе.
7. Проверить публичную ленту: fee-записи не должны содержать служебные comments.
