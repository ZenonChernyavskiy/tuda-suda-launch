# TONCENTER_SEND_BOC_JSON_FIX_REPORT

## Что было сломано

`sendBoc` не должен отправляться в Toncenter как form-urlencoded запрос. Для Toncenter API v2 нужен JSON POST.

Ошибка на сервере:

`TON Center HTTP 422: failed to parse post request: JSON parse error`

означала, что Toncenter ожидал JSON body, а получил тело в другом формате.

## Что исправлено

В `backend/app/ton_service.py` функция `send_boc()` приведена к JSON POST через `_toncenter_post_json()`:

```python
def send_boc(boc_base64: str) -> Any:
    payload = _toncenter_post_json("sendBoc", {"boc": boc_base64})
    if not payload.get("ok"):
        raise TonCenterError(str(payload.get("error") or payload))
    return payload.get("result")
```

`_toncenter_post_json()` отправляет:

- `Content-Type: application/json`
- `Accept: application/json`
- `X-API-Key`, если `TONCENTER_API_KEY` задан

## Что не менялось

- `run_get_method()` не менялся.
- Бизнес-логика покупки и payout не менялась.
- Hot wallet, подпись транзакции и построение BOC не менялись.
- Секреты и mnemonic не логируются.

## Как повторно запустить payout

1. Перезапустить backend после деплоя.
2. Повторить проверку подтвержденной покупки:

```http
POST /asset-deposits/28/verify
```

3. Если BOC корректный и Toncenter принимает транзакцию, payout должен продолжить выполнение и сохранить tx hash выплаты.
