# iris-client

Async Python client for the [Iris](https://github.com/wisepayru/iris) API. Wraps
the Iris HTTP endpoints (orders, items, slips) in an `httpx`-based client that
returns parsed Pydantic models, with built-in retries and trace-header
propagation.

Its request/response models are kept in lockstep with the Iris service; see
[`tests/`](tests/) for the contract-drift guard.

## Installation

Pinned to a release tag (the supported consumption path):

```bash
pip install git+https://github.com/wisepayru/iris-client.git@1.0.1
```

Released wheels/sdists are also attached to each
[GitHub Release](https://github.com/wisepayru/iris-client/releases).

Requires Python >= 3.14. Runtime deps: `httpx`, `pydantic`, `tenacity`.

## Usage

The client is an async context manager. Every call returns a
`(httpx.Request, httpx.Response, parsed_model)` tuple.

```python
from uuid import UUID
from iris_client import Client, models

async def example():
    async with Client(token="...", base_url="https://iris.example.com") as client:
        # create an order
        req, resp, order = await client.create_order(
            models.OrderCreateRequest(
                order_uuid=UUID("7eb92490-d4e7-4141-8af0-1510e8867ef2"),
                platform_name="YANDEX_MARKET",
                platform_order_id="57962644480",
                order_price=5196,
                platform_fee_amount=0,
            )
        )
        print(order.message)  # -> "Order created successfully"

        # fetch the actual slip for a SKU
        _, _, slip = await client.get_slip_by_sku("apple-1000")
        print(slip.slip)  # base64 payload
```

### Trace propagation

Every method takes an optional `headers=` dict that is merged onto the outgoing
request (the static auth/User-Agent headers are preserved). Use it to forward
trace/correlation IDs:

```python
await client.get_order(order_uuid, headers={"X-Trace-Id": trace_id})
```

## Methods

| Method | HTTP | Returns |
|---|---|---|
| `create_order(order_data, headers=None)` | `POST /order` | `OrderCreateResponse` |
| `get_order(order_uuid, headers=None)` | `GET /order/{uuid}` | `OrderResponse` |
| `get_order_items(order_uuid, headers=None)` | `GET /order/{uuid}/items` | `OrderItemsResponse` |
| `create_item(item_data, headers=None)` | `POST /item` | `ItemCreateResponse` |
| `get_item(item_uuid, headers=None)` | `GET /item/{uuid}` | `ItemCodeResponse` |
| `update_item_code(item_uuid, item_code, headers=None)` | `PUT /item/{uuid}/code` | `ItemCodeUpdateResponse` |
| `create_slip(slip_data, headers=None)` | `POST /slip` | `SlipCreateResponse` |
| `make_slip_actual(slip_uuid, headers=None)` | `POST /slip/{uuid}/makeActual` | `SlipActualUpdateResponse` |
| `get_slip_by_uuid(slip_uuid, headers=None)` | `GET /slip/{uuid}` | `SlipByUuidResponse` |
| `get_slips(sku=None, only_actual=True, headers=None)` | `GET /slips` | `list[SlipByUuidResponse]` |
| `get_slip_by_sku(item_sku, headers=None)` | `GET /sku/{sku}/slip` | `SlipBySkuResponse` |

Request/response model definitions live in
[`iris_client/models.py`](iris_client/models.py).

## Behavior

- **Auth:** `Client(token, base_url)` sends `Authorization: Bearer <token>` and a
  `wisepay-iris-client/<version>` User-Agent on every request. Both `token` and
  `base_url` are required.
- **Retries:** requests are retried up to 5 times (fixed 2s wait) on transport
  errors (connect/read/timeout) and transient server statuses
  (`429`, `502`, `503`, `504`). Permanent 4xx (e.g. `403`, `404`) raise
  immediately. On exhaustion the underlying `httpx` exception is re-raised
  (not wrapped in `tenacity.RetryError`).
- **Errors:** non-2xx responses raise `httpx.HTTPStatusError` via
  `raise_for_status()`.

## Development

```bash
python3.14 -m venv .venv
.venv/bin/pip install -e . -r requirements-test.txt
.venv/bin/ruff check .
.venv/bin/pytest
```

See [`tests/fixtures/README.md`](tests/fixtures/README.md) for fixture provenance.

## License

[MPL-2.0](LICENSE).
