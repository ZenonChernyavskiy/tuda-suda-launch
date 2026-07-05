# FIX TEST ISSUES REPORT

## Измененные файлы

- `backend/app/referral_service.py`
- `backend/app/main.py`
- `backend/app/providers/jetton.py`
- `backend/app/ton_service.py`
- `frontend/src/App.jsx`
- `frontend/src/api.js`
- `frontend/src/telegram.js`
- `FIX_TEST_ISSUES_REPORT.md`

## Реферальная ссылка

- Генерация ссылки приведена к Telegram-формату:
  - если `TELEGRAM_MINI_APP_SHORT_NAME` задан: `https://t.me/<BOT_USERNAME>/<TELEGRAM_MINI_APP_SHORT_NAME>?startapp=ref_<REFERRAL_CODE>`
  - если `TELEGRAM_MINI_APP_SHORT_NAME` не задан: `https://t.me/<BOT_USERNAME>?start=ref_<REFERRAL_CODE>`
- `TELEGRAM_BOT_USERNAME` и `TELEGRAM_MINI_APP_SHORT_NAME` дополнительно нормализуются от `@` и лишних `/`.
- Frontend теперь читает referral code из `startapp`, `start`, `ref`, `tgWebAppStartParam` и вложенного `tgWebAppData.start_param`.
- Backend больше не теряет `referralParam`, который frontend отправляет вместе с `initData`.
- Реферальная привязка теперь применяется и для уже существующего пользователя, если он еще не был привязан к referrer.
- Некорректный referral code игнорируется без падения приложения.

## Кнопка «Поделиться»

- Кнопка больше не открывает referral link напрямую как Telegram-пользователя или чат.
- В Telegram Mini App используется `https://t.me/share/url?...`.
- Если Telegram share недоступен, используется `navigator.share`.
- Если системный share недоступен или завершился ошибкой, ссылка копируется в буфер обмена.

## Упоминания TON в интерфейсе

- Пользовательские тексты про `TON`, `testnet`, `TON wallet`, `TON deposit`, `Jetton deposit` заменены на нейтральные формулировки про кошелек, пополнение и TDSD.
- В `Профиль -> Пополнить актив` текст заменен на `Кошелек подключен`.
- Пользовательские списки активов, подарков, лидерборда и пополнений фильтруются под `TDSD`, чтобы старые TON-записи не всплывали в интерфейсе.
- Технические TON/TonConnect имена в коде оставлены, потому что они нужны для интеграции кошелька и проверки переводов.

## TDSD deposits

- Английское техническое сообщение про contract deployment убрано из пользовательского пути.
- Если on-chain TDSD-пополнение выключено через `TDSD_DEPOSITS_ENABLED=false`, backend использует fixed-price покупку TDSD за TON.
- Если не хватает кошелька проекта для fixed-price покупки, backend возвращает: `Пополнение TDSD временно недоступно`.
- Ошибки проверки TDSD-пополнения переведены на нормальные русские сообщения.
- По текущему `.env.example` `TDSD_DEPOSITS_ENABLED=false`, поэтому на сервере используется покупка TDSD по фиксированной цене.

## Env на сервере

Проверить:

- `TELEGRAM_BOT_USERNAME` — username реального бота без `@`.
- `TELEGRAM_MINI_APP_SHORT_NAME` — short name Mini App; если он пустой, ссылки будут через `?start=ref_...`.
- `PUBLIC_APP_URL` — публичный HTTPS URL frontend.
- `PUBLIC_API_URL` — публичный HTTPS URL backend.
- `TDSD_DEPOSITS_ENABLED` — `false` для fixed-price покупки TDSD за TON, `true` только когда on-chain Jetton deposit реально готов.
- `TDSD_JETTON_MASTER_ADDRESS` — deployed TDSD master address.
- `TDSD_PROJECT_JETTON_WALLET` — project TDSD wallet address; обязателен при `TDSD_DEPOSITS_ENABLED=true`.
- `HOT_WALLET_ADDRESS` — hot wallet для fixed-price покупки при `TDSD_DEPOSITS_ENABLED=false`.
- `TDSD_FIXED_PRICE_TON` — фиксированная цена, сейчас `0.1`.
- `TON_NETWORK` — техническая сеть для провайдера, сейчас используется backend-интеграцией.

## Проверки

- Frontend build: `VITE_API_URL=http://localhost:8000 npm run build` — прошел.
- Backend compile: `python -m compileall app` — прошел.
- Backend `/health` во временном clean env: ответил `{"status":"ok","database":"connected"}`.
- Referral backend сценарий:
  - новый приглашенный пользователь привязался к referrer;
  - уже существующий непривязанный пользователь привязался к referrer;
  - некорректный referral code был проигнорирован без ошибки.
- `docker compose up` локально не проверен: на этой машине нет Docker CLI (`docker: command not found`). Нужно повторить на сервере или машине с Docker.

## Как протестировать после деплоя

1. Открыть вкладку `Рефералы` пользователем A и проверить формат ссылки.
2. Нажать `Скопировать` и убедиться, что ссылка копируется.
3. Нажать `Поделиться` в Telegram Mini App и убедиться, что открывается Telegram share, а не ошибка пользователя/чата.
4. Открыть ссылку пользователем B и проверить, что приложение открывается без ошибки `Пользователь не найден`.
5. Проверить в backend или UI рефералов, что B появился у A как приглашенный.
6. Открыть `Профиль -> Пополнить актив` и проверить текст `Кошелек подключен`.
7. Выбрать TDSD и проверить, что нет английского сообщения про deployment.
8. Если `TDSD_DEPOSITS_ENABLED=false`, проверить fixed-price покупку: `1 TDSD = 0.1 TON`, создание заявки, оплату через кошелек и подтверждение.
9. Если `TDSD_DEPOSITS_ENABLED=true`, проверить on-chain Jetton deposit, memo/комментарий и подтверждение.
10. На сервере выполнить `docker compose up --build`, затем проверить `/health`.
