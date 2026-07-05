# HOT_WALLET_PAYOUT_REPORT

## Что изменено

- Добавлен backend-сервис `backend/app/hot_wallet_payout.py` для подписания и отправки TDSD jetton transfer с hot wallet.
- В `backend/app/config.py` добавлено чтение `HOT_WALLET_MNEMONIC` и `HOT_WALLET_JETTON_TRANSFER_GAS_TON`.
- В `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/migrations.py` и Alembic-миграциях добавлены поля выплаты:
  - `payout_status`
  - `payout_tx_hash`
  - `payout_failed_reason`
  - `payout_sent_at`
  - `payout_confirmed_at`
- В `backend/app/main.py` выплата подключена к подтверждению fixed-price покупки TDSD.
- В `frontend/src/App.jsx` добавлены русские статусы покупки и выплаты.
- В `backend/requirements.txt` добавлена зависимость `tonsdk`.
- Обновлены `.env.example`, `.env.production.example`, `backend/.env.example`, `README.md`, `DEPLOYMENT.md`.

## Как работает выплата

1. Пользователь создает покупку TDSD по фиксированному курсу `1 TDSD = 0.1 TON`.
2. Backend проверяет входящую оплату TON на проектный адрес по сумме и комментарию.
3. После подтверждения оплаты backend применяет `PURCHASE_FEE_PERCENT`.
4. Net-сумма TDSD зачисляется на внутренний баланс и отправляется on-chain с hot wallet.
5. Для отправки backend получает hot wallet jetton wallet через `TDSD_JETTON_MASTER_ADDRESS`.
6. Backend подписывает стандартный jetton transfer через `HOT_WALLET_MNEMONIC`.
7. Hash исходящего сообщения сохраняется в `payout_tx_hash`, статус становится `sent`.

## Защита от повторной выплаты

- Перед отправкой backend ставит внутренний `pending:*` lock в `payout_tx_hash`.
- Если пользователь повторно нажмет проверку во время отправки, новая отправка не начнется.
- Если `payout_status` уже `sent` или `confirmed`, повторная выплата не выполняется.

## Ошибки и статусы для пользователя

- `Ожидаем оплату`
- `Оплата найдена`
- `Отправляем TDSD`
- `TDSD отправлены`
- `Ошибка отправки, обратитесь в поддержку`
- Если `HOT_WALLET_MNEMONIC` отсутствует: `Автоматическая выплата временно недоступна`

## Env на сервере

Проверить и выставить:

```env
HOT_WALLET_ADDRESS=
HOT_WALLET_MNEMONIC=
HOT_WALLET_JETTON_TRANSFER_GAS_TON=0.08
TDSD_JETTON_MASTER_ADDRESS=
PROJECT_TON_WALLET=
TDSD_FIXED_PRICE_TON=0.1
PURCHASE_FEE_PERCENT=1
TON_NETWORK=testnet
TONCENTER_API_URL=https://testnet.toncenter.com/api/v2
TONCENTER_API_KEY=
```

Hot wallet должен иметь запас TDSD и TON для gas. Treasury mnemonic на сервер не нужен и не должен храниться.

## Проверки

- Backend compile: пройден.
- Backend import с пустым `HOT_WALLET_MNEMONIC`: пройден, возвращает `Автоматическая выплата временно недоступна`.
- Frontend build: пройден.
- `/health`: `ok`.
- `/ready`: `ready`.

Реальная on-chain отправка не выполнялась локально, потому что для этого нужны production `HOT_WALLET_MNEMONIC`, запас TDSD/TON на hot wallet и реальная подтвержденная покупка.
