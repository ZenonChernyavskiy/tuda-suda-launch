# FIX_STAGE_UI_TOPUP_PROFILE_REPORT

## Измененные файлы

- `backend/alembic/versions/202606270001_stage8_initial_schema.py`
- `backend/app/main.py`
- `backend/app/migrations.py`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/security.py`
- `frontend/src/App.jsx`
- `frontend/src/styles.css`
- `frontend/src/telegram.js`

## Главная: удален блок Монеты

- С главного hero убрана отдельная карточка баланса, которая могла восприниматься как legacy-блок старых монет.
- Последние операции на Главной теперь строятся только из TDSD-подарков.
- Legacy virtual gift операции больше не попадают в Главную.
- Блок TDSD-баланса ниже оставлен как TDSD-only список, без упоминаний монет.

## Активы: скрыта информация о комиссиях

- В frontend добавлен фильтр fee-записей ledger: `fee`, `fee_purchase`, `fee_transfer`, `treasury_income`.
- В публичной ленте также скрыты `source_type=fee`.
- Старые `virtual_gift` записи с legacy-токеном не показываются в пользовательской ленте.
- Backend-логика комиссий не отключалась.

## Комиссия перевода 10%

- Значение по умолчанию остается в `backend/app/config.py`: `TRANSFER_COMMISSION_PERCENT=10`.
- В `backend/.env.example` и `.env.production.example` указано `TRANSFER_COMMISSION_PERCENT=10`.
- Проверенный расчет:
  - отправитель отправляет 100 TDSD;
  - отправитель списывает 100 TDSD;
  - получатель получает 90 TDSD;
  - комиссия платформы = 10 TDSD.

## Покупка TDSD

- Экран `Профиль -> Купить TDSD` теперь показывает fixed-rate покупку.
- Пользователь может вводить сумму в TDSD или TON.
- UI показывает:
  - `Курс: 1 TDSD = 0.1 TON`;
  - сколько TDSD покупается;
  - сколько TON нужно оплатить;
  - сколько TDSD будет зачислено после комиссии покупки.
- После создания покупки показываются:
  - сумма к покупке;
  - сумма к оплате в TON;
  - адрес проекта для оплаты;
  - кнопка `Скопировать адрес`;
  - обязательный комментарий;
  - кнопка `Оплатить через кошелек` через TonConnect.
- Если пользователь платит не через кнопку TonConnect, экран объясняет, что нужно отправить TON на указанный адрес и дождаться подтверждения.

## Кошелек оплаты TON

- Для fixed-price покупки используется `PROJECT_TON_WALLET`.
- Backend также отдает `project_ton_wallet_address` в `/fees/config`, чтобы frontend мог иметь актуальный адрес из env/config.
- На сервере нужно проверить, что `PROJECT_TON_WALLET` задан реальным project TON wallet.

## Telegram profile photo

- Backend сохраняет `photo_url` из Telegram Mini App initData.
- `photo_url` добавлен в модель пользователя, runtime migration, Alembic initial schema и `UserPublic`.
- `/auth/telegram` обновляет `photo_url` при входе.
- Frontend дополнительно читает `window.Telegram.WebApp.initDataUnsafe.user.photo_url`.
- В профиле показывается Telegram-фото, если оно есть.
- Если фото нет, остается текущий fallback avatar с инициалом.

## Env на сервере

Проверить:

- `TDSD_FIXED_PRICE_TON=0.1`
- `PROJECT_TON_WALLET=<project TON wallet>`
- `HOT_WALLET_ADDRESS=<hot wallet>`
- `TREASURY_WALLET_ADDRESS=<treasury wallet>`
- `TRANSFER_COMMISSION_PERCENT=10`
- `TDSD_DEPOSITS_ENABLED=false` для fixed-price покупки
- `TDSD_PROJECT_JETTON_WALLET=<project jetton wallet>` только если включается on-chain Jetton deposit

Новых обязательных env-переменных для Telegram photo нет.

## Проверки

- Frontend build: прошел.
- Backend compile: прошел.
- `/health`: `{"status":"ok","database":"connected"}`.
- `/ready`: `{"status":"ready","database":"connected"}`.
- Расчет комиссии перевода 100 TDSD: 90 TDSD получателю, 10 TDSD комиссия.
- Расчет покупки 100 TDSD: 10 TON к оплате, 99 TDSD к зачислению после 1% комиссии покупки.
- `photo_url` сохраняется и возвращается в `UserPublic`.
- `project_ton_wallet_address` возвращается в `/fees/config`.
- `docker compose` локально не проверен: Docker CLI отсутствует на машине (`docker: command not found`).

## Как протестировать после деплоя

1. Открыть вкладку `Главная`.
2. Убедиться, что отдельного блока старых монет нет.
3. Отправить TDSD-подарок и проверить, что последняя операция отображается как TDSD.
4. Открыть пользовательские списки TDSD/активов и убедиться, что нет визуальной информации о комиссиях.
5. Отправить 100 TDSD и проверить в backend ledger: 100 списано, 90 получено, 10 ушло в комиссию.
6. Открыть `Профиль -> Купить TDSD`.
7. Ввести 100 TDSD и проверить: `К оплате: 10 TON`, к зачислению после 1%: 99 TDSD.
8. Создать покупку и проверить, что показаны адрес проекта, комментарий и кнопка копирования адреса.
9. Оплатить через TonConnect или вручную по адресу, затем нажать `Проверить статус`.
10. Открыть профиль в Telegram Mini App: если у пользователя есть Telegram-фото, оно должно отображаться; если нет, должен остаться fallback avatar.
11. На сервере выполнить `docker compose up --build`.
12. Проверить `GET https://api.tudasuda.tech/health`.
