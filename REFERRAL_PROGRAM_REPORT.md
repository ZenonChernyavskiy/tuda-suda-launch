# Referral Program Report

## 1. Измененные файлы

- `backend/app/models.py`
- `backend/app/referral_service.py`
- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/app/security.py`
- `backend/app/config.py`
- `backend/app/migrations.py`
- `backend/alembic/versions/202607010001_referral_program.py`
- `backend/seed.py`
- `backend/.env.example`
- `.env.example`
- `.env.production.example`
- `frontend/src/App.jsx`
- `frontend/src/api.js`
- `frontend/src/telegram.js`
- `frontend/src/styles.css`
- `README.md`
- `DEPLOYMENT.md`

## 2. Новые таблицы и поля

В `users` добавлены поля:

- `referral_code`
- `referred_by_user_id`
- `referred_at`

Добавлена таблица `referral_rewards`:

- `id`
- `referrer_user_id`
- `referred_user_id`
- `purchase_id`
- `purchase_amount_tdsd`
- `reward_amount_tdsd`
- `reward_percent`
- `status`
- `created_at`
- `credited_at`

`purchase_id` используется для идемпотентности: за один TDSD deposit награда не начисляется повторно.

## 3. Backend API

Добавлен endpoint:

- `GET /referrals/me`

Он возвращает:

- referral code;
- готовую Telegram referral-ссылку;
- количество приглашенных;
- total/pending rewards;
- список приглашенных пользователей;
- историю начислений.

## 4. Referral Link

Если `TELEGRAM_MINI_APP_SHORT_NAME` пустой:

```text
https://t.me/tudasuda_tdsd_bot?start=ref_<REFERRAL_CODE>
```

Если `TELEGRAM_MINI_APP_SHORT_NAME` задан:

```text
https://t.me/tudasuda_tdsd_bot/<TELEGRAM_MINI_APP_SHORT_NAME>?startapp=ref_<REFERRAL_CODE>
```

В mock mode frontend также читает `startapp`, `start` или `ref` из URL.

## 5. Start Param Handling

Для реального Telegram входа backend использует только signed Telegram `initData`.
Обычный JSON `referralParam` принимается только в mock mode.

Это защищает production от подмены referral code на frontend.

## 6. Начисление 10%

Награда начисляется только после успешного подтверждения TDSD `AssetDeposit`.

Текущая формула:

```text
reward_units = purchase_amount_units * REFERRAL_REWARD_PERCENT / 100
```

По умолчанию:

```env
REFERRAL_REWARD_PERCENT=10
REFERRAL_REWARD_ASSET_SYMBOL=TDSD
```

Награда сразу зачисляется на `AssetBalance` пригласившего и фиксируется в `AssetLedgerEntry` с типом `referral_reward_credit`.

## 7. Frontend

Добавлена вкладка нижнего меню:

- `Главная`
- `Все`
- `Рефералы`
- `Профиль`

Вкладка `Рефералы` содержит:

- referral-ссылку;
- кнопки `Скопировать` и `Поделиться`;
- статистику `Приглашено`, `Получено`, `Ожидает`;
- список приглашенных пользователей;
- историю наград;
- короткие правила программы.

UI сохранен в текущей liquid glass теме.

## 8. Как проверить локально

1. Пересоздать backend окружение, если текущее `.venv` сломано:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Применить миграции:

```bash
alembic upgrade head
```

3. Запустить backend:

```bash
uvicorn app.main:app --reload
```

4. Запустить frontend:

```bash
cd frontend
npm install
npm run dev
```

5. Войти первым mock-пользователем, открыть вкладку `Рефералы`, скопировать ссылку.
6. Открыть frontend с параметром `?ref=ref_<CODE>` и выбрать другого mock-пользователя.
7. Подтвердить TDSD `AssetDeposit` для приглашенного пользователя.
8. Вернуться к пригласившему и проверить вкладку `Рефералы`, ledger и общий список `Все`.

## 9. Проверки

Выполнено:

- `python3 -m compileall app seed.py production_seed.py` - успешно.
- `npm run build` - успешно.

Не выполнено в текущей среде:

- `alembic upgrade head` через глобальный Python: Alembic CLI не установлен.
- `alembic upgrade head` через `backend/.venv`: локальное `.venv` содержит битый `sqlalchemy` namespace.
- `npm run dev`: sandbox не разрешил открыть порт `127.0.0.1:5173` (`listen EPERM`).
- `npm run dev -- --host 0.0.0.0 --port 5174`: тот же sandbox-запрет `listen EPERM`.

## 10. Ограничения

- Награда привязана к подтвержденному TDSD `AssetDeposit`, так как отдельного purchase-flow сейчас нет.
- Система одноуровневая.
- За регистрацию, gifts, transfer fees и обычные переводы награды не начисляются.
- Pending status предусмотрен архитектурно, но текущая реализация зачисляет награду сразу в одной DB transaction.

## 11. Production Readiness

Реферальный слой готов для testnet-проверки после применения миграций и пересоздания backend `.venv`.
Перед публичным запуском нужно пройти полный E2E с реальным Telegram Mini App startapp и подтвержденным TDSD deposit.
