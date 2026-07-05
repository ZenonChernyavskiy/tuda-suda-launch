# TONCENTER_RUN_GET_METHOD_FIX_REPORT

## Что было сломано

`backend/app/ton_service.py` вызывал Toncenter `runGetMethod` через GET-запрос с параметрами в query string.

Из-за этого `get_jetton_wallet_address()` падал на шаге:

`run_get_method(master_address, "get_wallet_address", stack)`

и Toncenter возвращал:

`TON Center HTTP 404: {"ok":false,"error":"Not Found","code":404}`

## Почему был 404

Toncenter API v2 ожидает вызов `runGetMethod` через:

`POST /api/v2/runGetMethod`

с JSON body:

```json
{
  "address": "contract address",
  "method": "method name",
  "stack": []
}
```

GET-вызов `/runGetMethod?...` не соответствовал ожидаемому формату endpoint.

## Что исправлено

- `run_get_method()` теперь вызывает `TONCENTER_API_URL + "/runGetMethod"` через POST.
- Body отправляется как JSON:
  - `address`
  - `method`
  - `stack`
- API key по-прежнему передается через header `X-API-Key`.
- Остальные методы Toncenter не изменялись:
  - `getWalletInformation`
  - `getTransactions`
  - `detectAddress`
  - `sendBoc`
- Добавлено логирование для `runGetMethod`:
  - endpoint;
  - address;
  - method;
  - наличие stack;
  - ответ Toncenter;
  - ошибка Toncenter с traceback.

Секреты, mnemonic/private key не логируются.

## Как проверить payout повторно

1. Перезапустить backend.
2. Повторить проверку уже подтвержденной покупки через существующий endpoint:

```http
POST /asset-deposits/<deposit_id>/verify
```

Например для покупки `#28`:

```http
POST /asset-deposits/28/verify
```

3. В логах должны появиться записи:
   - `Calling Toncenter runGetMethod ...`
   - `Toncenter runGetMethod response ...`
   - затем шаги `Resolving TDSD jetton wallet ...`
   - затем шаги отправки BOC.

Если Toncenter вернет ошибку, теперь в логах будет полный traceback и ответ Toncenter.
