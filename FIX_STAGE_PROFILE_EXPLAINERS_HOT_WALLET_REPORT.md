# FIX_STAGE_PROFILE_EXPLAINERS_HOT_WALLET_REPORT

## Измененные файлы

- `.env.example`
- `.env.production.example`
- `backend/.env.example`
- `backend/app/config.py`
- `frontend/src/App.jsx`
- `frontend/src/styles.css`
- `README.md`
- `DEPLOYMENT.md`
- `FEES_INTEGRATION_REPORT.md`
- `FIX_STAGE_TDSD_REFERRALS_TOPUP_REPORT.md`
- `FIX_STAGE_UI_TOPUP_PROFILE_REPORT.md`

## Hot wallet address

Актуальный адрес добавлен в backend defaults и env examples:

```env
PROJECT_TON_WALLET=UQCaKtJZrSwLgcYwGYSG9Qijyn73oRdXIinxx-zBQ752TXxo
HOT_WALLET_ADDRESS=UQCaKtJZrSwLgcYwGYSG9Qijyn73oRdXIinxx-zBQ752TXxo
```

Frontend не хранит адрес оплаты TDSD. Экран покупки показывает `target_wallet_address` из ответа backend на создание покупки.

За адрес приема оплаты TON отвечает `PROJECT_TON_WALLET`. Именно он попадает в `target_wallet_address` и показывается пользователю при покупке TDSD.

За адрес hot wallet, который подписывает и отправляет TDSD пользователю, отвечает `HOT_WALLET_ADDRESS`.

`HOT_WALLET_MNEMONIC` остается только на backend, не логируется и не передается во frontend.

## Popup в профиле

Во вкладке `Профиль` карточки `Репутация`, `Карма` и `Ранг` стали кликабельными.

Одинаковое поведение для всех трех popup:

- открываются по тапу на карточку;
- закрываются тапом по затемненному фону;
- закрываются кнопкой `Закрыть`;
- используют fixed bottom sheet с blur-фоном;
- адаптированы под мобильный экран Telegram Mini App;
- нижнее меню не меняется и не ломается.

## Ранги

Используется текущая backend-система рангов:

- `Новичок` — стартовый ранг;
- `Добряк` — карма от 50;
- `Меценат` — карма от 200;
- `Легенда` — карма от 500;
- `Титан` — карма от 1000.

В popup `Ранг` текущий ранг пользователя подсвечивается.

## Env перед деплоем

Проверить на сервере:

```env
PROJECT_TON_WALLET=UQCaKtJZrSwLgcYwGYSG9Qijyn73oRdXIinxx-zBQ752TXxo
HOT_WALLET_ADDRESS=UQCaKtJZrSwLgcYwGYSG9Qijyn73oRdXIinxx-zBQ752TXxo
HOT_WALLET_MNEMONIC=
HOT_WALLET_JETTON_TRANSFER_GAS_TON=0.08
TDSD_JETTON_MASTER_ADDRESS=
TDSD_FIXED_PRICE_TON=0.1
PURCHASE_FEE_PERCENT=1
```

Если `PROJECT_TON_WALLET` и `HOT_WALLET_ADDRESS` отличаются, пользователь увидит адрес оплаты из `PROJECT_TON_WALLET`, а TDSD будут отправляться с `HOT_WALLET_ADDRESS`.

## Проверки

- Старый hot wallet address в frontend/backend examples/docs не найден.
- Frontend build проходит.
- Backend compile проходит.
- `GET /health` возвращает `ok`.
- `GET /ready` возвращает `ready`.
- `/fees/config` возвращает новый `project_ton_wallet_address` и `hot_wallet_address`.
- `/asset-deposits/create` для `TDSD` возвращает новый `target_wallet_address`.
- Docker compose локально не проверен: на машине отсутствует Docker CLI.
