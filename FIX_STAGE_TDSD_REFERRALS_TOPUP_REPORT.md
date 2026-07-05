# FIX_STAGE_TDSD_REFERRALS_TOPUP_REPORT

## Измененные файлы

- `.env.production.example`
- `DEPLOYMENT.md`
- `E2E_TESTING.md`
- `FINAL_LAUNCH_READINESS_REPORT.md`
- `FIX_TEST_ISSUES_REPORT.md`
- `README.md`
- `REFERRAL_PROGRAM_REPORT.md`
- `backend/.env.example`
- `backend/app/config.py`
- `backend/app/fee_service.py`
- `backend/app/main.py`
- `backend/app/migrations.py`
- `backend/app/providers/__init__.py`
- `backend/app/providers/registry.py`
- `backend/app/providers/tdsd_fixed_price.py`
- `backend/app/schemas.py`
- `backend/production_seed.py`
- `contracts/.env.contracts.example`
- `contracts/deploy/TESTNET_DEPLOYMENT.md`
- `contracts/metadata/tdsd-metadata.json`
- `frontend/public/tdsd-metadata.json`
- `frontend/src/App.jsx`

## Реферальная ссылка

- Правильный Telegram bot username: `tudasuda_tdsd_bot`.
- Правильная базовая ссылка: `https://t.me/tudasuda_tdsd_bot`.
- `TELEGRAM_BOT_USERNAME` нормализуется без `@`.
- Если `TELEGRAM_MINI_APP_SHORT_NAME` пустой, backend генерирует:
  `https://t.me/tudasuda_tdsd_bot?start=ref_<REFERRAL_CODE>`.
- Если `TELEGRAM_MINI_APP_SHORT_NAME` задан, backend генерирует:
  `https://t.me/tudasuda_tdsd_bot/<TELEGRAM_MINI_APP_SHORT_NAME>?startapp=ref_<REFERRAL_CODE>`.
- Backend принимает referral param из `start_param`, `startapp`/frontend `referral_param` fallback и привязывает приглашенного пользователя один раз.
- Самоприглашение и некорректный referral code игнорируются без грубой ошибки для пользователя.

## Кнопка Поделиться

- Frontend использует Telegram share URL: `https://t.me/share/url?...`.
- В share передается уже готовая referral-ссылка на `tudasuda_tdsd_bot`.
- Если Telegram API/share недоступен, fallback копирует referral link в буфер обмена.

## Проверенные и исправленные ссылки

- Production frontend: `https://app.tudasuda.tech`.
- Production API: `https://api.tudasuda.tech`.
- Telegram bot: `https://t.me/tudasuda_tdsd_bot`.
- TonConnect manifest и TDSD metadata переведены на `app.tudasuda.tech`.
- Env examples, deployment docs, README, reports и contract env examples проверены.
- Подтверждение: неправильный Telegram bot username больше не используется.
- Подтверждение: старый `.site` домен больше не используется.

## Окно Отправить подарок

- Убраны пользовательские слова `монеты` и `активы` из сценария отправки подарка.
- Окно работает как TDSD-only сценарий: сумма TDSD, сообщение, кнопка `Отправить TDSD`.
- Отдельная визуальная карточка комиссии в окне отправки подарка убрана.
- Backend-логика комиссии подарка не менялась.

## Пополнение TDSD

- Добавлен fixed-price режим покупки TDSD за TON.
- Цена задается через `TDSD_FIXED_PRICE_TON=0.1`.
- Текущий курс: `1 TDSD = 0.1 TON`.
- Пример: 10 TON дают 100 TDSD gross; при `BUY_COMMISSION_PERCENT=1` на баланс зачисляется 99 TDSD.
- При `TDSD_DEPOSITS_ENABLED=false` backend использует provider `tdsd_fixed_price`.
- Для fixed-price покупки backend проверяет оплату по project wallet, сумме оплаты и комментарию.
- Seed/migration оставляют TDSD активным в fixed-price режиме даже до готового Jetton-деплоя.
- Пользовательский UI показывает курс, сумму TDSD, сумму к оплате и финальное зачисление после комиссии.
- Текст `кошелек готов к testnet-депозиту` заменен на `Кошелек подключен`.
- Технические сообщения вроде `Jetton deposits are disabled`, `contract deployment`, `testnet deposit` в UI не показываются.

## Env на сервере

Проверить и выставить:

- `TELEGRAM_BOT_USERNAME=tudasuda_tdsd_bot`
- `TELEGRAM_MINI_APP_SHORT_NAME=` или валидный short name Mini App
- `PUBLIC_APP_URL=https://app.tudasuda.tech`
- `PUBLIC_API_URL=https://api.tudasuda.tech`
- `FRONTEND_URL=https://app.tudasuda.tech`
- `VITE_APP_URL=https://app.tudasuda.tech`
- `VITE_API_URL=https://api.tudasuda.tech`
- `TDSD_FIXED_PRICE_TON=0.1`
- `TDSD_DEPOSITS_ENABLED=false` для fixed-price покупки
- `HOT_WALLET_ADDRESS=UQCaKtJZrSwLgcYwGYSG9Qijyn73oRdXIinxx-zBQ752TXxo` для fixed-price покупки
- `TON_NETWORK=testnet`
- `TDSD_JETTON_MASTER_ADDRESS=<master>` если on-chain Jetton уже задеплоен
- `TDSD_PROJECT_JETTON_WALLET=<project jetton wallet>` только для `TDSD_DEPOSITS_ENABLED=true`

`TDSD_DEPOSITS_ENABLED=true` включать только после готовности on-chain Jetton deposit.

## Проверки

- Link audit: старые bot/domain/example URL не найдены.
- Frontend build: `VITE_API_URL=http://localhost:8000 npm run build` прошел.
- Backend compile: `python -m compileall app production_seed.py` прошел.
- Referral fallback link: `https://t.me/tudasuda_tdsd_bot?start=ref_ABCD1234` проверен.
- Referral Mini App link: `https://t.me/tudasuda_tdsd_bot/tuda_suda?startapp=ref_ABCD1234` проверен.
- Referral attach: приглашенный пользователь привязался к referrer; invalid code проигнорирован.
- Fixed price quote: 100 TDSD -> 10 TON; после 1% комиссии -> 99 TDSD.
- Fixed provider check: при `TDSD_DEPOSITS_ENABLED=false` TDSD активен, provider `tdsd_fixed_price`, к оплате 10 TON за 100 TDSD.
- Backend `/health`: `{"status":"ok","database":"connected"}`.
- Backend `/ready`: `{"status":"ready","database":"connected"}`.
- `docker compose` локально не проверен: на машине нет Docker CLI (`docker: command not found`).

## Как тестировать после деплоя

1. Открыть `Рефералы` пользователем A.
2. Проверить, что ссылка ведет на `https://t.me/tudasuda_tdsd_bot`.
3. Нажать `Скопировать` и проверить буфер обмена.
4. Нажать `Поделиться` и убедиться, что Telegram открывает share без ошибки пользователя.
5. Открыть ссылку пользователем B и убедиться, что Mini App открывается.
6. Проверить, что B появился у A как приглашенный.
7. Открыть `Главная -> Отправить подарок`: нет слов `монеты` и `активы`, нет отдельной карточки комиссии.
8. Отправить TDSD и проверить, что backend-операция подарка работает.
9. Открыть `Профиль -> Пополнить актив`.
10. Проверить текст `Кошелек подключен`.
11. Выбрать TDSD и проверить курс `1 TDSD = 0.1 TON`.
12. Ввести 100 TDSD и проверить расчет `К оплате: 10 TON`, `На баланс будет зачислено: 99 TDSD`.
13. Создать покупку, оплатить через кошелек, затем нажать `Проверить статус`.
14. На сервере выполнить `docker compose up --build`.
15. Проверить `GET https://api.tudasuda.tech/health`.
