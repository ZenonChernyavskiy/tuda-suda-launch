# REMOVE_PROJECT_TON_WALLET_REPORT

## Измененные файлы

- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/providers/tdsd_fixed_price.py`
- `backend/app/providers/ton_native.py`
- `backend/app/schemas.py`
- `frontend/src/App.jsx`
- `.env.example`
- `.env.production.example`
- `backend/.env.example`
- `README.md`
- `DEPLOYMENT.md`
- `E2E_TESTING.md`
- `PRODUCTION_CHECKLIST.md`
- `FIX_TEST_ISSUES_REPORT.md`
- `FIX_STAGE_TDSD_REFERRALS_TOPUP_REPORT.md`
- `FIX_STAGE_UI_TOPUP_PROFILE_REPORT.md`
- `FIX_STAGE_PROFILE_EXPLAINERS_HOT_WALLET_REPORT.md`
- `HOT_WALLET_PAYOUT_REPORT.md`

## Где раньше использовался PROJECT_TON_WALLET

`PROJECT_TON_WALLET` использовался как адрес приема TON для fixed-price покупки TDSD и для старого native TON deposit flow.

Теперь основная логика покупки берет адрес оплаты через `get_tdsd_payment_wallet_address()`:

1. Сначала используется `HOT_WALLET_ADDRESS`.
2. Если `HOT_WALLET_ADDRESS` отсутствует, временно используется deprecated fallback `PROJECT_TON_WALLET`.
3. Если оба адреса отсутствуют, backend возвращает понятную ошибку, что адрес приема оплаты временно не настроен.

## Как выбирается payment_address

Для покупки TDSD backend создает deposit с `payment_address = HOT_WALLET_ADDRESS`.

В API `payment_address` добавлен в:

- `AssetDepositCreateResponse`;
- `AssetDepositPublic`;
- `/fees/config`.

Старое поле `target_wallet_address` оставлено для совместимости с существующей таблицей и старым frontend, но новый frontend читает `payment_address`.

## HOT_WALLET_ADDRESS

`HOT_WALLET_ADDRESS` теперь основной публичный адрес:

- пользователь отправляет TON на `HOT_WALLET_ADDRESS`;
- backend показывает этот адрес как `payment_address`;
- frontend не содержит hardcoded wallet address и показывает адрес из API.

## HOT_WALLET_MNEMONIC

`HOT_WALLET_MNEMONIC` используется только backend-сервисом payout для подписи jetton transfer.

Она не логируется, не сохраняется в базе, не возвращается через API и не попадает во frontend bundle.

## Env на сервере

Обязательные значения:

```env
HOT_WALLET_ADDRESS=UQCaKtJZrSwLgcYwGYSG9Qijyn73oRdXIinxx-zBQ752TXxo
HOT_WALLET_MNEMONIC=
TREASURY_WALLET_ADDRESS=
TDSD_FIXED_PRICE_TON=0.1
PURCHASE_FEE_PERCENT=1
TRANSFER_COMMISSION_PERCENT=10
```

Deprecated fallback:

```env
# Deprecated: use HOT_WALLET_ADDRESS instead.
# PROJECT_TON_WALLET=
```

Если `PROJECT_TON_WALLET` остается в существующем `.env.production`, он не мешает: при наличии `HOT_WALLET_ADDRESS` backend всегда использует hot wallet.

## Проверка после деплоя

1. Проверить, что `/fees/config` возвращает `payment_address` равный `HOT_WALLET_ADDRESS`.
2. Создать покупку TDSD и проверить, что ответ `/asset-deposits/create` содержит тот же `payment_address`.
3. Проверить, что frontend показывает этот адрес в блоке `Адрес для оплаты`.
4. Проверить, что кнопка `Оплатить через кошелёк` отправляет TON на `payment_address`.
5. Проверить, что `HOT_WALLET_MNEMONIC` не появляется в network response и frontend bundle.
6. Проверить, что `/health` и `/ready` отвечают успешно.

## Локальные проверки

- Backend compile проходит.
- Frontend build проходит.
- Backend стартует без `PROJECT_TON_WALLET`.
- `GET /health` возвращает `ok`.
- `GET /ready` возвращает `ready`.
- `/fees/config` возвращает `payment_address = HOT_WALLET_ADDRESS` и не отдает `project_ton_wallet_address`.
- `/asset-deposits/create` для TDSD возвращает `payment_address = HOT_WALLET_ADDRESS`.
- `HOT_WALLET_MNEMONIC` не найден во frontend source/bundle.
- Docker compose локально не проверен: на машине отсутствует Docker CLI.
