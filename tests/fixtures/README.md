# Test fixtures

Response bodies the client must parse, used by `tests/test_client.py` and
`tests/test_models.py`. Two provenances:

## Real captures (from OpenSearch `RequestLoggingMiddleware` logs, env `qa`)

Captured verbatim from the live `iris` service's request-logging middleware:

- `orders/order_create_response.json` — `POST /order` 200
- `orders/order_response.json` — `GET /order/{uuid}` 200
- `orders/order_items_response.json` — `GET /order/{uuid}/items` 200
- `items/item_create_response.json` — `POST /item` 200 (note `item_code: null`)
- `items/item_code_response.json` — `GET /item/{uuid}` 200
- `items/item_code_update_response.json` — `PUT /item/{uuid}/code` 200
- `slips/slip_by_sku_response.json` — `GET /sku/{item_sku}/slip` 200
- `errors/invalid_token_403.json` — `POST /order` 403 (bad bearer token)

## Spec-derived (built from `iris/main.py` response models)

The slip write/read response bodies were not present in the capture window, so
these are synthesized from the service's Pydantic response models. They reuse
real ids/sku/base64 values seen in the same capture's debug logs
(`slip_uuid=33dbf274-...`, `item_sku=apple-1000`, the Spotify base64 slip), and
match the service's serialization exactly:

- `slips/slip_create_response.json` — `SlipCreateResponse` (`{message, data: SlipResponse}`).
  `SlipResponse` has **no** custom serializer, so its timestamps keep
  microseconds + `+03:00` (default pydantic datetime isoformat); `actual_flg`
  is `false` (a freshly created slip).
- `slips/slip_actual_update_response.json` — `SlipActualUpdateResponse`.
- `slips/slip_by_uuid_response.json` — `SlipByUuidResponse`. Note the wire key
  is **`uuid`** (the model aliases `slip_uuid` → `uuid`) and the timestamps are
  microsecond-stripped Moscow-tz isoformat, per the model's `field_serializer`.
- `slips/slips_list_response.json` — `list[SlipByUuidResponse]`.

If real captures of the four slip responses become available, replace these and
drop this note.
