# Commission Update Report

## 1. Измененные файлы

- `backend/app/config.py`
- `backend/app/fee_service.py`
- `backend/app/main.py`
- `backend/app/schemas.py`
- `frontend/src/App.jsx`
- `.env.example`
- `.env.production.example`
- `backend/.env.example`
- `README.md`
- `DEPLOYMENT.md`
- `PRODUCTION_CHECKLIST.md`
- `FEES_INTEGRATION_REPORT.md`

## 2. Добавленные env-переменные

```env
BUY_COMMISSION_PERCENT=1
TRANSFER_COMMISSION_PERCENT=10
```

Старые активные fee-переменные `PURCHASE_FEE_PERCENT`, `PURCHASE_MIN_FEE_TON` и `TRANSFER_FEE_PERCENT` удалены из конфигурации и документации.

## 3. Новые комиссии

- Покупка TDSD: `1%`.
- Перевод / дар TDSD: `10%`.

При покупке TDSD комиссия удерживается из покупаемой суммы до зачисления на внутренний баланс. Пример: покупка 1000 TDSD дает пользователю +990 TDSD, комиссия системы составляет 10 TDSD.

При даре TDSD отправитель списывает ровно указанную сумму. Комиссия удерживается из суммы перевода. Пример: отправитель дарит 100 TDSD, получатель получает 90 TDSD, treasury получает 10 TDSD.

## 4. Backend-логика

- `fee_service.py` теперь рассчитывает покупку через `calculate_buy_commission`.
- `calculate_transfer_fee` использует `TRANSFER_COMMISSION_PERCENT=10` для TDSD.
- `/fees/config` возвращает новые значения комиссий, включая совместимые поля `buy_fee_percent`, `purchase_fee_percent`, `transfer_fee_percent`.
- Подтверждение TDSD deposit зачисляет пользователю сумму после 1% комиссии.
- Ledger фиксирует:
  - `deposit` на фактически зачисленную сумму;
  - `fee_purchase` для комиссии покупки;
  - `treasury_income` для дохода treasury;
  - `gift_sent`, `gift_received`, `fee_transfer`, `treasury_income` для даров.

## 5. Frontend

- На экране отправки дара показывается `Комиссия платформы: 10%`.
- Для TDSD-дара показывается расчет `Получатель получит` по введенной сумме.
- На экране пополнения TDSD показывается комиссия покупки `1%` и сумма, которая будет зачислена.
- UI-структура и TON Connect не менялись.

## 6. Проверки

Выполнено:

```text
python3 -m compileall app seed.py production_seed.py
npm run build
```

Обе проверки прошли успешно.

Проверены расчетные сценарии:

```text
buy 100: credited=99, commission=1
buy 1000: credited=990, commission=10
buy 10000: credited=9900, commission=100
transfer 100: receiver=90, commission=10
transfer 250: receiver=225, commission=25
transfer 1000: receiver=900, commission=100
```

`npm run dev -- --host 127.0.0.1 --port 5173` в среде Codex не смог открыть локальный порт из-за ограничения окружения:

```text
Error: listen EPERM: operation not permitted 127.0.0.1:5173
```

Это ограничение среды запуска, а не ошибка сборки приложения. Локально команду нужно проверить в обычном терминале.

## 7. Проверка старых значений

Проверен поиск по активному коду и документации:

- `PURCHASE_FEE_PERCENT`
- `PURCHASE_MIN_FEE_TON`
- `TRANSFER_FEE_PERCENT`
- `0.5%`

Старые значения комиссий больше не используются. В проекте остаются некомиссионные значения `0.5`, например быстрый выбор суммы TON и CSS-значения прозрачности.
