# Fees Integration Report

## 1. Что изменено

Добавлена конфигурация комиссий и treasury/hot wallet через env:

- `BUY_COMMISSION_PERCENT=1`
- `TRANSFER_COMMISSION_PERCENT=10`
- `TREASURY_WALLET_ADDRESS=UQAOgQnt-ZMtAsMWtnL9zFs1Id27b8L3gc35pvQZA4dmUZg6`
- `HOT_WALLET_ADDRESS=UQB-gyjeCOixVUyVx-X_4FqhXeOwjCIUYnkue4vQESUx6f66`
- `TDSD_JETTON_MASTER_ADDRESS=EQBZkfdol6WOj-GXByKLeRlo70ktYIQnTA5Hq_gT6KVYvY3n`

Старый `GIFT_FEE_BPS` оставлен для совместимости, но новая TDSD transfer fee логика использует `TRANSFER_COMMISSION_PERCENT`.

## 2. Backend

Добавлен модуль `backend/app/fee_service.py`.

Он считает:

- purchase fee;
- transfer fee;
- treasury amount;
- recipient amount;
- total amount.

Добавлены endpoints:

- `GET /fees/config`
- `POST /fees/purchase/quote`
- `POST /fees/transfer/quote`

## 3. TDSD gift fee logic

Для TDSD asset gift:

- sender списывает полную сумму `X`;
- fee считается как `X * TRANSFER_COMMISSION_PERCENT / 100`;
- receiver получает `X - fee`;
- treasury получает `fee` во внутренний `AssetBalance`;
- отрицательные балансы невозможны;
- inactive asset использовать нельзя;
- сумма `0`, отрицательная сумма и сумма меньше/равная комиссии отклоняются.

Для TON asset gift комиссия сейчас `0%`, чтобы не менять уже работающую логику TON.

## 4. Ledger

Ledger теперь фиксирует комиссии отдельными типами:

- `fee_purchase` - комиссия TDSD-покупки;
- `fee_transfer` - audit-запись комиссии TDSD-подарка у отправителя;
- `treasury_income` - зачисление комиссии treasury.

Для успешного TDSD gift создаются:

- `gift_sent`;
- `gift_received`;
- `fee_transfer`;
- `treasury_income`.

Admin ledger показывает все комиссии. Публичная вкладка “Все транзакции” показывает gift и системную комиссию treasury как отдельную операцию.

## 5. Frontend

На форме отправки asset gift добавлен компактный блок:

- `Вы отправляете: ... TDSD`;
- `Комиссия платформы: 10%`;
- `Получатель получит: ... TDSD`;
- `Комиссия сети TON оплачивается кошельком отдельно`.

Для покупки TDSD frontend показывает, что из покупки удерживается 1%.

Liquid glass тема, вкладки “Главная”, “Все”, “Профиль”, TON Connect и отображение TON/TDSD не менялись.

## 6. TON Connect limitation

Текущий frontend по-прежнему не импортирует `@ton/core` и не строит Jetton transfer payload в браузере, чтобы не вернуть проблему `Buffer is not defined`.

Полноценная on-chain некастодиальная TDSD transfer-операция через TON Connect с двумя Jetton messages:

1. transfer net amount получателю;
2. transfer fee в Treasury Wallet;

пока не включена в браузерный flow. Текущий gift flow остается внутренней off-chain операцией через `AssetBalance` и `AssetLedgerEntry`.

Для будущего этапа нужно отдельно реализовать browser-safe Jetton payload builder или подключить проверенную browser-compatible библиотеку без Node polyfills.

## 7. Измененные файлы

- `backend/app/config.py`
- `backend/app/fee_service.py`
- `backend/app/asset_gift_service.py`
- `backend/app/main.py`
- `backend/app/schemas.py`
- `frontend/src/api.js`
- `frontend/src/App.jsx`
- `frontend/src/styles.css`
- `.env.example`
- `.env.production.example`
- `backend/.env.example`
- `README.md`
- `DEPLOYMENT.md`
- `PRODUCTION_CHECKLIST.md`
- `E2E_TESTING.md`

## 8. Проверки

Выполнено:

- `python3 -m compileall backend/app` - успешно;
- `npm install` - успешно;
- `npm run build` - успешно.

`npm run dev -- --host 127.0.0.1 --port 5173` в среде Codex не запустился из-за ограничения открытия локального порта: `listen EPERM`. Локально в VS Code нужно проверить обычной командой `npm run dev`.

Дополнительная runtime-проверка backend через старое локальное `backend/.venv` не прошла, потому что в этом venv поврежден/не установлен `python-dotenv`: `ImportError: cannot import name 'load_dotenv' from 'dotenv'`. После чистого `pip install -r backend/requirements.txt` это нужно перепроверить локально.
