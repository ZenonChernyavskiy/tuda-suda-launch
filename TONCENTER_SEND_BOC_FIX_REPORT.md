# TONCENTER_SEND_BOC_FIX_REPORT

## Что было сломано

`backend/app/ton_service.py` отправлял `sendBoc` через общий `_toncenter_post()` helper с телом `application/x-www-form-urlencoded`.

При payout TDSD ошибка возникала на шаге:

`send_tdsd_from_hot_wallet() -> send_boc(boc_base64) -> _toncenter_post("sendBoc", {"boc": boc_base64})`

Toncenter возвращал:

`TON Center HTTP 422: {"ok":false,"error":"failed to parse post request: JSON parse error at line 1 column 1: Invalid value.","code":422}`

## Почему был HTTP 422

Toncenter API v2 для `sendBoc` ожидает JSON body:

```json
{
  "boc": "<base64 boc>"
}
```

Старый вызов отправлял form-urlencoded body, поэтому Toncenter пытался разобрать тело как JSON и падал с ошибкой парсинга.

## Что исправлено

- `send_boc()` теперь вызывает `POST /api/v2/sendBoc` через JSON helper.
- Body отправляется как:

```json
{
  "boc": "<base64 boc>"
}
```

- Заголовки:
  - `Content-Type: application/json`
  - `Accept: application/json`
- API key по-прежнему передается через `X-API-Key`.
- `runGetMethod` не изменялся.
- Бизнес-логика payout не менялась.
- Добавлено логирование для `sendBoc`:
  - endpoint;
  - длина BOC;
  - наличие API key без вывода ключа;
  - ответ Toncenter;
  - ошибка Toncenter с traceback.

Содержимое BOC, mnemonic/private key и другие секреты не логируются.

## Как повторно запустить payout

1. Перезапустить backend после деплоя.
2. Повторить проверку уже подтвержденной покупки через существующий endpoint:

```http
POST /asset-deposits/<deposit_id>/verify
```

Для покупки `#28`:

```http
POST /asset-deposits/28/verify
```

3. В логах должны появиться записи:
   - `Calling Toncenter sendBoc ...`
   - `Toncenter sendBoc response ...`
   - затем статус выплаты должен перейти в `sent`, если Toncenter принял BOC.

Если Toncenter вернет новую ошибку, она будет записана с полным traceback и ответом Toncenter.
