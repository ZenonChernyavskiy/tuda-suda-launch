# Stage 4 v2 Audit — Туда-Сюда

## Итог

Stage 4 v2 реализует правильный архитектурный поворот: внутренняя экономика больше не завязана напрямую на `user.ton_balance_nano`, а вынесена в универсальный слой активов.

Текущий статус: **готово к Stage 5 после небольшого review**.

Оценка: **8.7/10**.

## Что проверено

- Backend компилируется через `python -m compileall app`.
- FastAPI app импортируется.
- Базовые endpoints отвечают:
  - `GET /health`
  - `POST /auth/telegram`
  - `GET /me`
  - `GET /assets`
  - `GET /assets/balances`
  - `GET /assets/ledger`
  - `GET /ton/balance`
- Frontend собирается через `npm run build`.
- Mock deposit со статусом `confirmed` начисляет AssetBalance и создает AssetLedgerEntry.
- TON asset сидится автоматически.
- Legacy `ton_balance_nano` мигрируется в `asset_balances`.

## Реализовано правильно

### Asset layer

Добавлены модели:

- `Asset`
- `AssetBalance`
- `AssetLedgerEntry`

Это правильная база для будущего собственного Jetton-токена.

Сейчас актив:

```text
TON / native / ton_testnet / decimals=9
```

В будущем можно добавить:

```text
TUDA / jetton / ton_mainnet или ton_testnet / decimals=9 / contract_address=<Jetton Master>
```

### AssetBalance

Баланс хранится в `balance_units` как integer. Для TON это nanotons.

Это правильно: не надо считать деньги через float.

### AssetLedgerEntry

Появился аудит экономики:

- deposit
- gift_sent
- gift_received
- adjustment
- fee

Для Stage 5 этого уже почти достаточно.

### TON deposit flow

При подтверждении TON deposit теперь:

1. создается/обновляется `AssetBalance`;
2. создается `AssetLedgerEntry`;
3. legacy `user.ton_balance_nano` синхронизируется только для совместимости.

Это правильная архитектура.

## Что я исправил в audited-версии

### 1. TON Center API error больше не переводит депозит в failed

Временная ошибка внешнего API не должна навсегда ломать депозит. Теперь депозит остается `pending`, а пользователь может повторить проверку.

### 2. Похожая транзакция с неправильным memo больше не фейлит депозит сразу

Если пользователь отправил похожую транзакцию без нужного memo, депозит не должен сразу становиться failed, потому что правильная транзакция еще может прийти до timeout.

## Замечания

### 1. `ton_balance_nano` лучше постепенно вывести из основного UI

Сейчас он остается для совместимости. Это нормально, но Stage 5 должен опираться на `AssetBalance`.

### 2. Старые виртуальные `transactions` не надо смешивать с реальными asset gifts

Для Stage 5 нужно создать отдельные таблицы:

- `asset_gifts`
- или `ton_gifts`, если хочешь временно сузить до TON

Лучше универсально: `AssetGift`.

### 3. Нужно добавить debit helper

Сейчас есть `credit_asset_balance`, но для Stage 5 нужен парный helper:

```python
debit_asset_balance(...)
```

Он должен:
- проверять достаточный баланс;
- уменьшать `AssetBalance.balance_units`;
- создавать ledger entry с `direction='debit'`.

### 4. Stage 5 должен быть database-only

Не нужно делать on-chain transfer пользователю. На Stage 5 подарок должен перемещать внутренний баланс:

```text
AssetBalance(sender) -= amount
AssetBalance(receiver) += amount
```

Withdrawals — отдельный этап.

## Рекомендованная цель Stage 5

**Внутренние случайные подарки активами.**

Пользователь выбирает актив, например TON, и сумму. Backend случайно выбирает получателя, списывает баланс отправителя, начисляет получателю и пишет ledger.

## Что не делать на Stage 5

- Не делать withdrawals.
- Не делать Jetton smart contract.
- Не делать mainnet.
- Не делать USDT.
- Не отправлять реальные on-chain транзакции между пользователями.
- Не удалять старые виртуальные подарки, пока новая экономика не протестирована.

## Следующая архитектура

Добавить модель `AssetGift`:

```text
id
sender_id
receiver_id
asset_id
amount_units
message
status
created_at
```

Статусы:

```text
completed
failed
cancelled
```

При успешном подарке создавать два ledger entry:

1. sender:
   - entry_type = gift_sent
   - direction = debit

2. receiver:
   - entry_type = gift_received
   - direction = credit

## Вывод

Stage 4 v2 хорошо подготовил проект под собственный токен. Теперь можно реализовывать Stage 5: внутренние подарки выбранным asset, начиная с TON, а позже тем же механизмом подключить собственный Jetton.
