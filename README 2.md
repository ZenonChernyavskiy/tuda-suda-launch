# Туда-Сюда

MVP Telegram Mini App, где пользователи отправляют виртуальные подарки случайным людям. В приложении есть виртуальные монеты, карма, анонимные сообщения, история, лидерборд, TON Connect и testnet-пополнение внутреннего TON-баланса. Mainnet, smart contracts, USDT/Jettons, withdrawals и реальные выплаты не используются.

## Структура

```text
tuda-suda/
  backend/
    app/
    requirements.txt
    seed.py
  frontend/
    public/
    src/
    package.json
  README.md
```

## Backend

```bash
cd tuda-suda/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

После запуска API будет доступен на `http://localhost:8000`, Swagger UI: `http://localhost:8000/docs`.

Seed-скрипт создает тестовых пользователей с Telegram ID `1001`-`1006`. Это нужно, чтобы случайная отправка работала локально: для подарка в базе должно быть минимум два пользователя.

## Frontend

```bash
cd tuda-suda/frontend
npm install
cp .env.example .env
npm run dev
```

Откройте `http://localhost:5173`. Если приложение запущено не внутри Telegram, оно автоматически включит mock mode и войдет как тестовый пользователь. В профиле можно переключаться между seed-пользователями.

Если npm ругается на права в `~/.npm`, используйте локальный cache проекта:

```bash
npm install --cache .npm-cache
npm_config_cache=.npm-cache npm run dev
```

Frontend использует `@tonconnect/ui-react` и `@ton/core`. Если зависимости уже были установлены до этапа 2, обновите их:

```bash
cd tuda-suda/frontend
npm install @tonconnect/ui-react @ton/core --cache .npm-cache
```

## Локальная проверка

1. Запустите backend на `http://localhost:8000`.
2. Выполните `python seed.py` в папке `backend`.
3. Запустите frontend на `http://localhost:5173`.
4. Откройте приложение, отправьте подарок, проверьте историю и лидерборд.
5. Откройте профиль, подключите TON-кошелек и сохраните адрес.
6. Укажите `PROJECT_TON_WALLET` в backend `.env`, затем проверьте вкладку `TON`.

## Telegram Mini App

Для будущего подключения к Telegram:

1. Создайте бота через BotFather.
2. Получите token и укажите его в `backend/.env` как `TELEGRAM_BOT_TOKEN`.
3. Разместите frontend и backend на HTTPS-доменах.
4. Укажите публичный URL frontend как Mini App URL в BotFather.
5. Укажите публичный backend URL во frontend-переменной `VITE_API_URL`.
6. В production отключите mock-login: `ALLOW_MOCK_AUTH=false`.

Frontend отправляет Telegram WebApp `initData` на `POST /auth/telegram`. Backend проверяет подпись `initData`, создает пользователя при первом входе и возвращает простой Bearer-токен для запросов MVP.

## Этап 2: TON Connect

На этом этапе реализована только привязка адреса TON-кошелька к пользователю. Реальные TON-переводы, USDT/Jettons, smart contracts и вывод средств пока не реализованы.

Что добавлено:

- frontend dependency: `@tonconnect/ui-react`;
- `TonConnectUIProvider` в React-приложении;
- TON-блок в профиле пользователя;
- краткий TON-статус на главном экране;
- backend-поля `ton_wallet_address` и `ton_wallet_connected_at`;
- endpoints для сохранения, чтения и отключения кошелька.
- отдельная backend-валидация TON-адресов без TON SDK.

Manifest лежит здесь:

```text
frontend/public/tonconnect-manifest.json
```

Локальный manifest:

```json
{
  "url": "http://localhost:5173",
  "name": "Tuda-Suda",
  "iconUrl": "http://localhost:5173/tonconnect-icon.svg"
}
```

Frontend env:

```env
VITE_API_URL=http://localhost:8000
VITE_APP_URL=http://localhost:5173
VITE_TONCONNECT_MANIFEST_URL=http://localhost:5173/tonconnect-manifest.json
```

Перед deploy нужно заменить local URLs на публичные HTTPS URLs:

- `frontend/public/tonconnect-manifest.json`: поля `url` и `iconUrl`;
- `frontend/.env`: `VITE_API_URL`, `VITE_APP_URL`, `VITE_TONCONNECT_MANIFEST_URL`;
- настройки Mini App в BotFather.

Как проверить в mock mode:

1. Запустите backend и frontend.
2. Откройте `http://localhost:5173`.
3. Перейдите в `Профиль`.
4. Нажмите `Подключить TON кошелек`.
5. Подключите кошелек через TON Connect.
6. После подключения нажмите `Сохранить кошелек`.
7. Убедитесь, что адрес отображается в профиле и на главном экране.
8. Нажмите `Отключить кошелек` и проверьте, что адрес удалился.

Как проверить внутри Telegram Mini App:

1. Разместите frontend/backend на HTTPS.
2. Обновите `tonconnect-manifest.json` на публичные HTTPS URLs.
3. Укажите публичный frontend URL в BotFather.
4. Откройте Mini App из Telegram.
5. Подключите кошелек, нажмите `Сохранить кошелек`, затем проверьте профиль.

## Этап 3: TON testnet deposits

Реализован testnet deposit flow: пользователь создает депозит, отправляет testnet TON через TON Connect на общий кошелек проекта, backend проверяет транзакцию через TON Center testnet API и начисляет внутренний `ton_balance_nano`.

Mainnet, smart contracts, USDT/Jettons, withdrawals и реальные случайные выплаты не реализованы.

### Env для testnet deposits

В `backend/.env`:

```env
APP_ENV=development
ALLOW_MOCK_AUTH=true
TON_NETWORK=testnet
PROJECT_TON_WALLET=
TONCENTER_API_URL=https://testnet.toncenter.com/api/v2
TONCENTER_API_KEY=
TONCENTER_TX_LIMIT=100
MIN_DEPOSIT_TON=0.05
MAX_DEPOSIT_TON=5
DEPOSIT_CONFIRMATION_TIMEOUT_MINUTES=30
```

`PROJECT_TON_WALLET` обязателен для создания реального testnet-депозита. Если он пустой, `POST /ton/deposits/create` вернет понятную ошибку.

`TONCENTER_API_KEY` можно оставить пустым, если лимиты TON Center позволяют. Для стабильной проверки лучше получить API key.

`TONCENTER_TX_LIMIT` управляет тем, сколько последних транзакций backend смотрит при проверке депозита. По умолчанию используется `100`.

### Как создать testnet TON wallet проекта

1. Создайте отдельный TON wallet в кошельке, который поддерживает testnet.
2. Переключите wallet в testnet mode.
3. Скопируйте адрес проекта.
4. Укажите его в `backend/.env` как `PROJECT_TON_WALLET`.
5. Используйте только testnet TON, не mainnet.

### Где получить testnet TON

Используйте testnet faucet для TON или testnet-раздел вашего кошелька. Отправляйте только небольшие суммы, например `0.05 TON`.

### Как создать и проверить депозит

1. Запустите backend и frontend.
2. Откройте Mini App.
3. В профиле подключите TON-кошелек через TON Connect.
4. Нажмите `Сохранить кошелек`.
5. Перейдите во вкладку `TON`.
6. Выберите сумму: `0.05`, `0.1`, `0.5` или введите свою.
7. Нажмите `Создать депозит`.
8. Нажмите `Оплатить через TON кошелек`.
9. Подтвердите transaction в кошельке.
10. Через 5-20 секунд нажмите `Проверить статус`.
11. Если backend найдет matching transaction, депозит станет `confirmed`, а `ton_balance_nano` увеличится.

Где хранится адрес кошелька:

- таблица `users`;
- поле `ton_wallet_address`;
- поле `ton_wallet_connected_at`;
- поле `ton_balance_nano`;
- legacy-поле `ton_balance` оставлено только для совместимости со старыми локальными базами.

Модель `TonDeposit`:

- `id`;
- `user_id`;
- `wallet_address`;
- `target_wallet_address`;
- `network`;
- `amount_ton`;
- `amount_nano`;
- `tx_hash`;
- `comment`;
- `status`: `pending`, `confirmed`, `failed`;
- `failed_reason`;
- `created_at`;
- `confirmed_at`.

Для локальной разработки есть mock endpoints:

- `POST /ton/deposits/mock`;
- `GET /ton/deposits`.

`POST /ton/deposits/mock` работает только в dev/mock режиме. В production укажите:

```env
APP_ENV=production
ALLOW_MOCK_AUTH=false
```

Это dev-заглушка, а не production payment flow.

Пример mock-депозита:

```json
{
  "amount_ton": 1.5,
  "tx_hash": "testnet-demo-tx-001",
  "status": "pending"
}
```

Если у пользователя уже сохранен TON-кошелек, `wallet_address` можно не передавать. Для явной проверки можно передать:

```json
{
  "amount_ton": 1.5,
  "tx_hash": "testnet-demo-tx-002",
  "status": "confirmed",
  "wallet_address": "0:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

Как проверить SQLite migration:

1. Запустите backend со старой SQLite-базой.
2. Backend при старте вызовет безопасную инициализацию.
3. `ensure_user_wallet_columns()` проверит `PRAGMA table_info(users)`.
4. Если колонок `ton_wallet_address`, `ton_wallet_connected_at`, `ton_balance` или `ton_balance_nano` нет, она добавит их.
5. Если старое поле `ton_balance` уже заполнено, а `ton_balance_nano` пустой, значение будет перенесено как `ton_balance * 1_000_000_000`.
6. `ensure_ton_deposit_columns()` добавит недостающие колонки депозитов, включая `failed_reason`.
7. Если колонки уже есть, миграция ничего не меняет.

Backend проверяет:

- recipient совпадает с `PROJECT_TON_WALLET`;
- sender совпадает с сохраненным кошельком пользователя на момент создания депозита;
- сумма transaction не меньше `amount_ton`;
- memo/comment совпадает с `deposit.comment`;
- `tx_hash` не использован в другом confirmed deposit.

## Stage 3 fixes before Stage 4

Перед Stage 4 проект подготовлен к дальнейшей работе с TON-балансом:

- внутренний TON-баланс теперь хранится как `ton_balance_nano`, то есть целое количество nanotons;
- `1 TON = 1_000_000_000 nanotons`;
- API возвращает оба поля: `ton_balance_nano` для точных расчетов и `ton_balance` для отображения;
- старое поле `ton_balance` не используется для расчетов, но остается в SQLite для совместимости;
- безопасная SQLite-миграция переносит старое decimal-значение в `ton_balance_nano`, если новая колонка пустая;
- у `TonDeposit` появилось поле `failed_reason`, чтобы видеть причину ошибки депозита;
- поиск транзакций TON Center использует `TONCENTER_TX_LIMIT=100` вместо жестких 30 транзакций;
- mock endpoint `/ton/deposits/mock` закрыт в production.

`failed_reason` заполняется, если:

- транзакция не найдена до timeout;
- сумма меньше ожидаемой;
- отправитель не совпадает с сохраненным кошельком;
- получатель не совпадает с кошельком проекта;
- memo/comment не совпадает;
- `tx_hash` уже использован;
- TON Center API вернул ошибку.

На этом этапе по-прежнему не реализованы внутренние TON-подарки, вывод средств, smart contracts, mainnet, USDT/Jettons и реальные выплаты.

## Stage 4: Asset-based economy

Stage 4 подготовил универсальный слой активов, чтобы сейчас продолжал работать TON testnet, а позже можно было добавить собственный TON Jetton token без переписывания всей экономики.

Что добавлено:

- `Asset` — справочник активов;
- `AssetBalance` — баланс пользователя по конкретному активу;
- `AssetLedgerEntry` — прозрачная история изменения балансов.

Сейчас автоматически создается только один asset:

```text
symbol: TON
name: Toncoin
asset_type: native
network: ton_testnet
decimals: 9
contract_address: null
is_active: true
```

Баланс хранится в smallest units:

- для TON это nanotons;
- `1 TON = 1_000_000_000 nanotons`;
- для будущего Jetton это будут smallest units по `decimals`;
- float не используется для расчетов.

`User.ton_balance_nano` оставлен для совместимости со старым Stage 3 API, но главным источником баланса стал `AssetBalance.balance_units`. При старте backend безопасно переносит старое `ton_balance_nano` в `AssetBalance` для `TON`, если такого баланса еще нет.

Когда TON deposit подтверждается:

1. `TonDeposit` получает статус `confirmed`.
2. `AssetBalance` пользователя по `TON` увеличивается на `deposit.amount_nano`.
3. Создается `AssetLedgerEntry`:
   - `entry_type = deposit`;
   - `direction = credit`;
   - `amount_units = deposit.amount_nano`;
   - `related_entity_type = ton_deposit`;
   - `related_entity_id = deposit.id`.
4. Legacy-поле `User.ton_balance_nano` обновляется как зеркало.

Frontend теперь показывает:

- блок `Балансы` на главном экране;
- вкладку `Активы`;
- список активов;
- балансы пользователя;
- ledger entries.

Как позже добавить собственный Jetton token:

```text
symbol = TUDA
name = Tuda Token
asset_type = jetton
network = ton_testnet или ton_mainnet
decimals = 9
contract_address = адрес Jetton Master
is_active = true
```

Автоматически `TUDA` сейчас не создается, потому что Jetton Master contract еще неизвестен. Smart contract, withdrawals, USDT/Jettons, mainnet и реальные выплаты на этом этапе не реализованы.

## Stage 5: Asset-based random gifts

Stage 5 добавляет внутренние случайные подарки активами через `AssetBalance`.

Это не on-chain transfer. Blockchain по-прежнему используется только для уже реализованного deposit flow. Сам подарок происходит внутри базы:

1. отправитель выбирает asset, например `TON`;
2. frontend отправляет сумму в smallest units;
3. backend выбирает случайного получателя;
4. `AssetBalance` отправителя уменьшается;
5. `AssetBalance` получателя увеличивается;
6. создается `AssetGift`;
7. создаются ledger entries `gift_sent` и `gift_received`;
8. отправителю начисляется karma.

Модель `AssetGift`:

- `id`;
- `sender_id`;
- `receiver_id`;
- `asset_id`;
- `amount_units`;
- `fee_units`;
- `net_amount_units`;
- `message`;
- `status`;
- `created_at`.

Комиссия задается через:

```env
GIFT_FEE_BPS=0
TREASURY_USER_ID=
```

`GIFT_FEE_BPS` — basis points:

- `0` = 0%;
- `100` = 1%;
- `300` = 3%.

Если комиссия появится, отправитель будет списывать полную сумму, получатель получать `net_amount_units`, а ledger будет содержать entry типа `fee`. Treasury-зачисление пока оставлено как будущий шаг.

Старые виртуальные подарки не удалены и продолжают работать отдельно. Asset gifts имеют отдельную историю и отдельный leaderboard.

Собственный Jetton позже добавляется как новый `Asset`:

```text
symbol = TUDA
name = Tuda Token
asset_type = jetton
network = ton_testnet или ton_mainnet
contract_address = адрес Jetton Master
decimals = 9
is_active = true
```

Jetton smart contract, withdrawals, USDT/Jettons, mainnet и прямые on-chain transfers на Stage 5 не реализованы.

## Stage 6: Asset Engine v2 and Provider Abstraction

Stage 6 отделяет экономику приложения от конкретной blockchain-логики. Теперь депозит создается не как “TON-only операция”, а как generic `AssetDeposit`, который выбирает provider по данным `Asset`.

Что добавлено:

- `backend/app/providers/base.py` — общий интерфейс asset provider;
- `backend/app/providers/ton_native.py` — provider для native TON testnet;
- `backend/app/providers/registry.py` — registry, который выбирает provider по `asset_type` и `network`;
- `AssetDeposit` — универсальная модель депозита в smallest units;
- endpoints `/asset-deposits/create`, `/asset-deposits/{id}/verify`, `/asset-deposits`;
- frontend-вкладка пополнения теперь asset-oriented и использует generic deposit API.

Зачем это нужно:

- сейчас работает `TON` как `native` asset в `ton_testnet`;
- позже можно добавить `TUDA` как `jetton` asset и написать `JettonProvider`;
- подарки, балансы и ledger уже работают через `AssetBalance`, поэтому бизнес-логика не должна зависеть от конкретного токена.

`AssetDeposit` хранит:

- пользователя;
- asset;
- кошелек отправителя;
- кошелек проекта;
- `amount_units`;
- provider;
- network;
- memo/comment;
- tx_hash;
- статус `pending`, `confirmed` или `failed`.

Для TON `amount_units` — это nanotons. Для будущего Jetton это будут smallest token units по `decimals`. Float для расчетов не используется.

Как сейчас работает native TON deposit:

1. Frontend создает `POST /asset-deposits/create` с `asset_symbol=TON`.
2. Backend находит `Asset(TON)` и выбирает `TonNativeProvider`.
3. Provider возвращает project wallet, amount, memo/comment и provider name.
4. Пользователь отправляет testnet TON через TON Connect.
5. Frontend вызывает `POST /asset-deposits/{id}/verify`.
6. Provider проверяет транзакцию через TON Center testnet API.
7. При подтверждении backend увеличивает `AssetBalance`, создает ledger entry `deposit` и зеркалит legacy `User.ton_balance_nano`.

Старые TON endpoints сохранены для совместимости:

- `POST /ton/deposits/create`;
- `POST /ton/deposits/{id}/verify`;
- `GET /ton/deposits`;
- `GET /ton/balance`.

Они пока остаются в проекте, но новый frontend flow использует generic `/asset-deposits/...`.

Future Jetton placeholder:

```text
symbol = TUDA
name = Tuda Token
asset_type = jetton
network = ton_testnet
contract_address = <Jetton Master address>
decimals = 9
is_active = true
```

Этот asset не создается автоматически, потому что Jetton Master contract еще не развернут и не проверен. Для будущего этапа нужно будет добавить `JettonProvider`, проверку Jetton transfer notification или иной надежный источник событий, правила treasury/accounting и отдельный security review.

Smart contract, withdrawals, USDT/Jettons, mainnet и реальные выплаты на Stage 6 по-прежнему не реализованы.

## Stage 7: Jetton-ready Asset Layer

Stage 7 готовит проект к будущему собственному Jetton-токену, не включая реальные Jetton-транзакции. Архитектура остается off-chain для внутренних подарков: пользователь отправляет asset gift внутри базы, backend списывает и начисляет `AssetBalance`, а аудит фиксируется через `AssetLedgerEntry`.

Что изменилось:

- у `Asset` появились `provider_key`, `metadata_json`, `display_order`;
- `GET /assets` возвращает только активные assets;
- `GET /admin/assets` показывает все assets, включая будущие неактивные токены;
- `POST /admin/assets/create` позволяет создать dev/admin asset-заготовку;
- добавлен `JettonProvider` placeholder, который явно сообщает, что Jetton deposits пока не реализованы;
- добавлены `/admin/ledger/all` и `/ledger/all` для просмотра общего ledger всех пользователей;
- лимиты внутренних asset-подарков по количеству и минимальной сумме отключены для MVP-тестирования.

Базовые проверки asset-подарков остались:

- пользователь должен быть авторизован;
- asset должен быть активным;
- `amount_units` должен быть больше 0;
- у отправителя должно хватать баланса;
- получатель не может быть отправителем;
- в системе должно быть минимум два пользователя.

Пример будущего собственного токена:

```json
{
  "symbol": "TUDA",
  "name": "Tuda Token",
  "asset_type": "jetton",
  "network": "ton_testnet",
  "decimals": 9,
  "contract_address": null,
  "provider_key": "jetton",
  "display_order": 10,
  "is_active": false
}
```

Такой asset лучше создавать неактивным (`is_active=false`), пока нет проверенного `Jetton Master address`. Неактивные assets не попадают в отправку подарков и deposit flow, но видны в dev/admin блоке “Будущие активы”.

Чтобы позже включить свой Jetton, нужно будет:

1. Развернуть и проверить Jetton smart contract.
2. Записать `contract_address` Jetton Master в `Asset`.
3. Реализовать настоящий `JettonProvider` для проверки deposit events.
4. Провести security review accounting, ledger и provider-логики.
5. Только после этого перевести asset в `is_active=true`.

Smart contract, withdrawals, USDT, mainnet и реальные Jetton deposits на Stage 7 не реализованы.

## Endpoints

### `GET /health`

Проверка состояния API и подключения к базе.

### `POST /auth/telegram`

Авторизация через Telegram `initData` или локальный mock-login.

Telegram payload:

```json
{
  "initData": "query_id=..."
}
```

Локальный payload:

```json
{
  "mock": true,
  "mock_user": {
    "telegram_id": "1001",
    "username": "demo_user",
    "first_name": "Demo"
  }
}
```

### `GET /me`

Возвращает профиль текущего пользователя, ранг и последние 5 операций. В профиле есть `ton_balance_nano` и отображаемый `ton_balance`.

### `POST /gift/send`

Отправляет подарок случайному пользователю.

```json
{
  "amount": 5,
  "message": "Хорошего дня!"
}
```

Ограничения:

- сумма только `1`, `5`, `10`, `25`;
- нельзя отправить больше текущего баланса;
- нельзя отправить самому себе;
- в базе должно быть минимум два пользователя;
- дневной лимит: 20 отправок на пользователя.

### `GET /transactions`

Возвращает историю отправленных и полученных подарков текущего пользователя.

### `GET /leaderboard`

Возвращает топ-100 пользователей в трех списках:

- `karma` — топ по карме;
- `senders` — топ по отправленным монетам;
- `receivers` — топ по полученным монетам.

### `GET /assets`

Возвращает список активных активов. Сейчас это `TON`, позже сюда можно добавить Jetton asset.

### `GET /admin/assets`

Dev/admin endpoint. Возвращает все assets: активные и неактивные. В production его нужно закрыть admin-role авторизацией.

### `POST /admin/assets/create`

Dev/admin endpoint для создания asset-заготовки. По умолчанию будущие токены стоит создавать неактивными.

```json
{
  "symbol": "TUDA",
  "name": "Tuda Token",
  "asset_type": "jetton",
  "network": "ton_testnet",
  "decimals": 9,
  "contract_address": null,
  "provider_key": "jetton",
  "metadata_json": {
    "note": "Future Jetton asset placeholder"
  },
  "display_order": 10,
  "is_active": false
}
```

### `GET /assets/balances`

Возвращает балансы текущего пользователя по всем активным активам.

Пример:

```json
[
  {
    "symbol": "TON",
    "name": "Toncoin",
    "balance_units": 150000000,
    "balance_display": "0.15",
    "decimals": 9
  }
]
```

### `GET /assets/ledger`

Возвращает asset ledger entries текущего пользователя: депозиты, будущие подарки, корректировки и комиссии.

### `GET /admin/ledger/all`

Alias: `GET /ledger/all`.

Dev/admin endpoint. Возвращает общий ledger всех пользователей на базе `AssetLedgerEntry`. В production его нужно закрыть admin-role авторизацией.

Поддерживает query params:

- `limit` — по умолчанию `100`;
- `offset` — по умолчанию `0`;
- `asset_symbol` — например `TON`;
- `user_id` — ID пользователя;
- `entry_type` — `deposit`, `gift_sent`, `gift_received`, `adjustment`, `fee`;
- `direction` — `credit` или `debit`.

Ответ включает пользователя, Telegram ID, asset, сумму, display-сумму, баланс после операции, related entity, комментарий и дату.

### `GET /assets/{symbol}/balance`

Возвращает баланс конкретного актива, например `GET /assets/TON/balance`.

### `POST /asset-deposits/create`

Создает generic asset deposit через provider registry. Сейчас поддержан `TON` через `ton_native`.

```json
{
  "asset_symbol": "TON",
  "amount_units": 100000000
}
```

Ответ содержит `deposit_id`, `asset_symbol`, `amount_units`, `amount_display`, `target_wallet_address`, `comment`, `provider`, `network` и `status`.

### `POST /asset-deposits/{deposit_id}/verify`

Проверяет deposit через provider выбранного asset. Для `TON` backend проверяет testnet transaction через TON Center API.

Если transaction подтверждена:

- `AssetDeposit.status` становится `confirmed`;
- `AssetBalance` пользователя увеличивается;
- создается `AssetLedgerEntry` с `entry_type = deposit`;
- для `TON` обновляется legacy-зеркало `User.ton_balance_nano`.

### `GET /asset-deposits`

Возвращает generic deposits текущего пользователя. Новый frontend flow использует этот endpoint для вкладки пополнения.

### `POST /asset-gifts/send-random`

Отправляет внутренний asset-подарок случайному пользователю.

Alias: `POST /asset-gifts/send`.

```json
{
  "asset_symbol": "TON",
  "amount_units": 10000000,
  "message": "Купи себе кофе"
}
```

Backend:

- проверяет актив;
- проверяет, что сумма больше 0;
- проверяет баланс отправителя;
- выбирает случайного получателя;
- списывает `amount_units` у отправителя;
- начисляет `net_amount_units` получателю;
- создает `AssetGift`;
- создает ledger entries;
- начисляет karma.

Stage 7 не ограничивает количество внутренних asset-подарков в день/час и не задает минимальную сумму выше `amount_units > 0`. Это сделано для быстрых MVP-тестов; production anti-abuse можно вернуть в `enforce_asset_gift_limits`.

### `GET /asset-gifts`

Возвращает историю asset-подарков текущего пользователя: отправленные и полученные.

### `GET /asset-gifts/leaderboard?symbol=TON`

Возвращает top-100 отправителей и получателей по выбранному asset.

### `POST /wallet/connect`

Сохраняет TON-адрес текущего пользователя.

```json
{
  "wallet_address": "EQ..."
}
```

MVP-валидация поддерживает:

- user-friendly TON-адреса длиной 48 символов с префиксом `EQ`, `UQ` или `kQ`;
- символы base64url: `A-Z`, `a-z`, `0-9`, `_`, `-`;
- raw format `0:<64 hex>` или `-1:<64 hex>`.

### `GET /wallet/me`

Возвращает текущий сохраненный TON-адрес пользователя.

### `DELETE /wallet/disconnect`

Удаляет сохраненный TON-адрес пользователя.

### `POST /ton/deposits/create`

Создает pending testnet-депозит.

```json
{
  "amount_ton": 0.1
}
```

Возвращает `deposit_id`, `target_wallet_address`, `amount_nano`, `comment`, `network`, `status`.

### `POST /ton/deposits/{deposit_id}/verify`

Проверяет депозит через TON Center testnet API. Начисляет `AssetBalance` по `TON` только если transaction подтверждена backend-проверкой. Legacy-поле `ton_balance_nano` обновляется как зеркало. В ответе возвращаются `ton_balance_nano`, `ton_balance` и депозит с `failed_reason`, если проверка завершилась ошибкой.

### `GET /ton/balance`

Возвращает внутренний TON-баланс текущего пользователя из `AssetBalance`:

```json
{
  "ton_balance_nano": 150000000,
  "ton_balance": 0.15
}
```

### `POST /ton/deposits/mock`

Создает mock-депозит для разработки. Доступен только в dev/mock режиме и закрыт при `APP_ENV=production`.

### `GET /ton/deposits`

Возвращает список TON-депозитов текущего пользователя, включая `failed_reason`.

## Ранги

| Карма | Ранг |
| --- | --- |
| 0-49 | Новичок |
| 50-199 | Добряк |
| 200-499 | Меценат |
| 500-999 | Легенда |
| 1000+ | Титан |

## Что намеренно не сделано в MVP

- mainnet-платежи;
- USDT/Jettons;
- smart contracts;
- вывод средств;
- реальные случайные выплаты;
- сложная JWT/OAuth-авторизация;
- production-ready антифрод.

Этот проект нужен как простое рабочее демо для проверки идеи.
