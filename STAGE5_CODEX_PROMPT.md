# Codex Prompt — Stage 5: Asset-based random gifts

Ты — опытный full-stack разработчик. У меня есть Telegram Mini App проект “Туда-Сюда”.

Текущий статус:
- Stage 1: виртуальные подарки реализованы
- Stage 2: TON Connect реализован
- Stage 3: TON testnet deposits реализованы
- Stage 4: Asset layer реализован
- есть модели Asset, AssetBalance, AssetLedgerEntry
- TON deposit подтверждается и начисляет AssetBalance
- в будущем планируется собственный TON Jetton-токен
- сейчас актив TON уже есть как Asset

Нужно выполнить Stage 5: внутренние случайные подарки через AssetBalance.

ВАЖНО:
- НЕ делать withdrawals
- НЕ делать smart contract
- НЕ создавать Jetton сейчас
- НЕ делать mainnet
- НЕ делать on-chain transfer между пользователями
- НЕ удалять старые виртуальные подарки
- НЕ ломать TON deposit flow
- Все переводы на этом этапе происходят только внутри базы данных

## Цель Stage 5

Пользователь должен иметь возможность отправить часть своего внутреннего asset-баланса случайному пользователю.

Пример:
1. Пользователь пополнил TON через testnet deposit.
2. У него появился AssetBalance TON.
3. Он выбирает “Отправить asset gift”.
4. Выбирает актив TON и сумму.
5. Backend случайно выбирает другого пользователя.
6. Backend списывает TON units у отправителя.
7. Backend начисляет TON units получателю.
8. Создаются ledger entries.
9. Обновляются asset leaderboard и история asset gifts.

## Backend task 1. Добавить модель AssetGift

Создать SQLAlchemy model AssetGift:

- id
- sender_id
- receiver_id
- asset_id
- amount_units
- message
- status
- created_at

status:
- completed
- failed
- cancelled

Связи:
- sender -> User
- receiver -> User
- asset -> Asset

Индексы:
- sender_id
- receiver_id
- asset_id
- created_at

## Backend task 2. Добавить безопасную SQLite migration

Добавить создание/проверку таблицы `asset_gifts`.

Если таблица уже есть — ничего не делать.

Не внедрять Alembic.

## Backend task 3. Добавить debit helper

Сейчас есть credit helper.

Добавить функцию:

```python
debit_asset_balance(
    db,
    user,
    asset,
    amount_units,
    entry_type,
    related_entity_type=None,
    related_entity_id=None,
    comment=None,
)
```

Логика:
- amount_units > 0
- найти или создать AssetBalance
- если balance_units < amount_units — HTTP 400 “Недостаточно средств”
- уменьшить balance_units
- создать AssetLedgerEntry:
  - direction = debit
  - entry_type = gift_sent
  - amount_units = amount_units
  - balance_after_units = новый баланс

## Backend task 4. Добавить asset gift endpoint

Добавить endpoint:

POST /asset-gifts/send-random

Request:
```json
{
  "symbol": "TON",
  "amount_units": 10000000,
  "message": "Купи себе кофе"
}
```

Логика:
- пользователь авторизован
- asset существует и is_active=true
- amount_units > 0
- проверить минимум/максимум для MVP
- у отправителя достаточно AssetBalance
- в базе есть хотя бы один другой пользователь
- выбрать случайного получателя, кроме отправителя
- желательно выбирать только пользователей, у которых есть telegram account; wallet не обязателен
- создать AssetGift со статусом completed
- списать amount_units у отправителя через debit helper
- начислить amount_units получателю через credit helper
- создать ledger entries:
  - sender: gift_sent / debit
  - receiver: gift_received / credit
- вернуть gift + новые балансы отправителя

Важно:
Операция должна быть атомарной. Если что-то падает — rollback.

## Backend task 5. Добавить историю asset gifts

Endpoints:

GET /asset-gifts

Возвращает подарки текущего пользователя:
- отправленные
- полученные
- сортировка по created_at desc
- limit 1..100

Response должен показывать:
- id
- type: sent или received
- symbol
- asset name
- amount_units
- amount_display
- message
- counterparty display name или анонимно
- created_at

## Backend task 6. Добавить asset leaderboard

Endpoint:

GET /asset-gifts/leaderboard?symbol=TON

Вернуть топ-100:
- top senders by total sent amount_units
- top receivers by total received amount_units

Не смешивать со старым leaderboard виртуальных монет.

## Backend task 7. Pydantic schemas

Добавить схемы:

- AssetGiftSendRequest
- AssetGiftPublic
- AssetGiftSendResponse
- AssetGiftLeaderboardUser
- AssetGiftLeaderboardResponse

## Frontend task 1. Добавить экран “Asset Gift”

Можно обновить вкладку “Дар” или добавить отдельный режим:
- “Виртуальные монеты”
- “Активы”

Для Stage 5 лучше сделать на вкладке “Дар” переключатель:

1. Виртуальный подарок
2. Asset-подарок

Asset gift UI:
- выбрать asset из `/assets/balances`
- показать доступный баланс
- выбрать сумму
- input в display units, например 0.01 TON
- преобразовать в units по decimals
- message input
- кнопка “Отправить случайному пользователю”

## Frontend task 2. Не использовать float для units

Для преобразования display amount -> units использовать string/BigInt.

Например:
- asset.decimals = 9
- “0.01” -> 10000000 units

## Frontend task 3. История

Добавить отображение asset gifts в истории или на отдельном блоке:
- отправленные
- полученные
- amount_display + symbol
- message
- date

## Frontend task 4. Leaderboard

Добавить asset leaderboard:
- по отправленным TON
- по полученным TON

Можно сделать отдельный блок на странице “Активы”.

## README

Обновить README:

Добавить раздел:

“Stage 5: Asset-based random gifts”

Описать:
- подарки происходят внутри базы
- это не on-chain transfer
- withdrawals пока нет
- smart contract пока нет
- собственный Jetton можно будет добавить как новый Asset позже

## Testing

Проверить:

Backend:
- app запускается
- GET /health
- auth mock
- создать 2 пользователей
- mock confirmed deposit одному пользователю
- POST /asset-gifts/send-random списывает баланс
- получателю начисляется баланс
- ledger содержит debit и credit
- GET /asset-gifts работает
- GET /asset-gifts/leaderboard работает
- старые virtual gifts работают
- TON deposits не сломаны

Frontend:
- npm install
- npm run build
- balances отображаются
- asset gift отправляется
- история отображается
- старые экраны не сломаны

## Итоговый отчет

После выполнения напиши:
1. Какие файлы изменены
2. Какие модели добавлены
3. Как работает asset gift
4. Как работает списание и начисление
5. Как работает ledger
6. Как проверить Stage 5
7. Что делать на Stage 6
