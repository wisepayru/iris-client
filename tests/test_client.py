"""Behavioral tests for iris_client.Client.

Every request is served by an in-memory httpx.MockTransport (see conftest's
``mock_iris``); no network is touched. We assert three things per method:
the outgoing request (verb, path, body), that the ``headers=`` trace-propagation
param (#10) reaches the wire, and that the response parses into the right model.
"""

import json
from uuid import UUID

import httpx
import pytest

from iris_client import Client, models

BASE_URL = "http://iris.test"
TOKEN = "test-token"
TRACE = {"X-Trace-Id": "trace-123", "X-Request-Id": "req-456"}

ITEM_UUID = UUID("e3ab0598-28aa-4055-aef7-e19448e7caab")
ORDER_UUID = UUID("ce3bac49-e15d-4d1c-9e41-8d9a5fb8fc52")
SLIP_UUID = UUID("33dbf274-4c1c-4287-a774-31f6d70d16af")


def make_client() -> Client:
    return Client(token=TOKEN, base_url=BASE_URL)


# --- auth / base-url -------------------------------------------------------

async def test_auth_header_and_base_url(mock_iris, load_fixture):
    mock_iris.respond_json(load_fixture("orders/order_response.json"))
    async with make_client() as client:
        await client.get_order(ORDER_UUID)

    req = mock_iris.last_request
    assert req.headers["Authorization"] == f"Bearer {TOKEN}"
    assert req.headers["User-Agent"].startswith("wisepay-iris-client/")
    assert str(req.url) == f"{BASE_URL}/order/{ORDER_UUID}"


async def test_uninitialized_client_raises():
    # Calling a method without `async with` leaves self._client None.
    client = make_client()
    with pytest.raises(RuntimeError, match="not initialized"):
        await client.get_order(ORDER_UUID)


# --- request building + response parsing, per method -----------------------

async def test_get_item(mock_iris, load_fixture):
    body = load_fixture("items/item_code_response.json")
    mock_iris.respond_json(body)
    async with make_client() as client:
        req, resp, parsed = await client.get_item(ITEM_UUID)

    assert mock_iris.last_request.method == "GET"
    assert mock_iris.last_request.url.path == f"/item/{ITEM_UUID}"
    assert isinstance(parsed, models.ItemCodeResponse)
    assert parsed.item_uuid == ITEM_UUID
    assert parsed.item_sku == body["item_sku"]


async def test_update_item_code(mock_iris, load_fixture):
    mock_iris.respond_json(load_fixture("items/item_code_update_response.json"))
    async with make_client() as client:
        req, resp, parsed = await client.update_item_code(ITEM_UUID, "123123123131")

    sent = mock_iris.last_request
    assert sent.method == "PUT"
    assert sent.url.path == f"/item/{ITEM_UUID}/code"
    assert json.loads(sent.content) == {"item_code": "123123123131"}
    assert isinstance(parsed, models.ItemCodeUpdateResponse)
    assert parsed.item_code == "123123123131"


async def test_update_item_code_accepts_none(mock_iris, load_fixture):
    body = dict(load_fixture("items/item_code_update_response.json"))
    body["item_code"] = None
    mock_iris.respond_json(body)
    async with make_client() as client:
        await client.update_item_code(ITEM_UUID, None)
    assert json.loads(mock_iris.last_request.content) == {"item_code": None}


async def test_create_item(mock_iris, load_fixture):
    body = load_fixture("items/item_create_response.json")
    mock_iris.respond_json(body)
    item = models.ItemCreateRequest(
        item_uuid=UUID("222f0ba0-1e0d-49d8-91b4-b1854a8cf447"),
        item_sku="apple-giftcard-500-try",
        item_code=None,
        item_price=1299,
        item_cost=0,
        order_uuid=UUID("7eb92490-d4e7-4141-8af0-1510e8867ef2"),
        platform_name="YANDEX_MARKET",
        platform_order_id="57962644480",
        platform_item_id="1124062679",
    )
    async with make_client() as client:
        req, resp, parsed = await client.create_item(item)

    sent = mock_iris.last_request
    assert sent.method == "POST"
    assert sent.url.path == "/item"
    # body is model_dump(mode="json"): UUIDs serialized as strings
    assert json.loads(sent.content) == item.model_dump(mode="json")
    assert isinstance(parsed, models.ItemCreateResponse)
    assert parsed.item_code is None
    assert parsed.message == "Item created successfully"


async def test_create_order(mock_iris, load_fixture):
    body = load_fixture("orders/order_create_response.json")
    mock_iris.respond_json(body)
    order = models.OrderCreateRequest(
        order_uuid=UUID("7eb92490-d4e7-4141-8af0-1510e8867ef2"),
        platform_name="YANDEX_MARKET",
        platform_order_id="57962644480",
        order_price=5196,
        platform_fee_amount=0,
    )
    async with make_client() as client:
        req, resp, parsed = await client.create_order(order)

    sent = mock_iris.last_request
    assert sent.method == "POST"
    assert sent.url.path == "/order"
    assert json.loads(sent.content) == order.model_dump(mode="json")
    assert isinstance(parsed, models.OrderCreateResponse)
    assert parsed.order_uuid == order.order_uuid


async def test_get_order(mock_iris, load_fixture):
    body = load_fixture("orders/order_response.json")
    mock_iris.respond_json(body)
    async with make_client() as client:
        req, resp, parsed = await client.get_order(ORDER_UUID)

    assert mock_iris.last_request.url.path == f"/order/{ORDER_UUID}"
    assert isinstance(parsed, models.OrderResponse)
    assert parsed.platform_name == body["platform_name"]
    assert parsed.order_price == body["order_price"]


async def test_get_order_items(mock_iris, load_fixture):
    body = load_fixture("orders/order_items_response.json")
    mock_iris.respond_json(body)
    async with make_client() as client:
        req, resp, parsed = await client.get_order_items(ORDER_UUID)

    assert mock_iris.last_request.url.path == f"/order/{ORDER_UUID}/items"
    assert isinstance(parsed, models.OrderItemsResponse)
    assert parsed.order_uuid == ORDER_UUID
    assert len(parsed.items) == len(body["items"]) == 2


async def test_create_slip(mock_iris, load_fixture):
    body = load_fixture("slips/slip_create_response.json")
    mock_iris.respond_json(body)
    slip = models.SlipCreateRequest(item_sku="apple-1000", slip="aGVsbG8=")
    async with make_client() as client:
        req, resp, parsed = await client.create_slip(slip)

    sent = mock_iris.last_request
    assert sent.method == "POST"
    assert sent.url.path == "/slip"
    assert json.loads(sent.content) == {"item_sku": "apple-1000", "slip": "aGVsbG8="}
    assert isinstance(parsed, models.SlipCreateResponse)
    assert parsed.data.slip_uuid == SLIP_UUID
    assert parsed.data.actual_flg is False


async def test_make_slip_actual(mock_iris, load_fixture):
    body = load_fixture("slips/slip_actual_update_response.json")
    mock_iris.respond_json(body)
    async with make_client() as client:
        req, resp, parsed = await client.make_slip_actual(SLIP_UUID)

    sent = mock_iris.last_request
    assert sent.method == "POST"
    assert sent.url.path == f"/slip/{SLIP_UUID}/makeActual"
    assert sent.content == b""  # no request body
    assert isinstance(parsed, models.SlipActualUpdateResponse)
    assert parsed.slip_uuid == SLIP_UUID


async def test_get_slip_by_uuid(mock_iris, load_fixture):
    body = load_fixture("slips/slip_by_uuid_response.json")
    mock_iris.respond_json(body)
    async with make_client() as client:
        req, resp, parsed = await client.get_slip_by_uuid(SLIP_UUID)

    assert mock_iris.last_request.url.path == f"/slip/{SLIP_UUID}"
    assert isinstance(parsed, models.SlipByUuidResponse)
    # the wire key is "uuid"; the model exposes it as slip_uuid
    assert parsed.slip_uuid == SLIP_UUID
    assert parsed.actual_flg is True
    assert parsed.created_dttm.utcoffset() is not None  # tz-aware parsed


async def test_get_slip_by_sku(mock_iris, load_fixture):
    body = load_fixture("slips/slip_by_sku_response.json")
    mock_iris.respond_json(body)
    async with make_client() as client:
        req, resp, parsed = await client.get_slip_by_sku("spotify-giftcard-usa-3-month")

    assert mock_iris.last_request.url.path == "/sku/spotify-giftcard-usa-3-month/slip"
    assert isinstance(parsed, models.SlipBySkuResponse)
    assert parsed.slip == body["slip"]


# --- get_slips query-param building ----------------------------------------

async def test_get_slips_default(mock_iris, load_fixture):
    mock_iris.respond_json(load_fixture("slips/slips_list_response.json"))
    async with make_client() as client:
        req, resp, parsed = await client.get_slips()

    params = mock_iris.last_request.url.params
    assert params.get("onlyActual") == "true"
    assert "sku" not in params
    assert isinstance(parsed, list)
    assert all(isinstance(s, models.SlipByUuidResponse) for s in parsed)
    assert parsed[0].slip_uuid == SLIP_UUID


async def test_get_slips_with_sku(mock_iris, load_fixture):
    mock_iris.respond_json(load_fixture("slips/slips_list_response.json"))
    async with make_client() as client:
        await client.get_slips(sku="apple-1000")

    params = mock_iris.last_request.url.params
    assert params.get("sku") == "apple-1000"
    assert params.get("onlyActual") == "true"


async def test_get_slips_only_actual_false_is_sent(mock_iris, load_fixture):
    # #14: only_actual=False must be sent so the server returns non-actual slips
    # (it defaults onlyActual=True when the param is absent).
    mock_iris.respond_json(load_fixture("slips/slips_list_response.json"))
    async with make_client() as client:
        await client.get_slips(only_actual=False)

    assert mock_iris.last_request.url.params.get("onlyActual") == "false"


# --- trace-header propagation (#10) across every method --------------------

# (id, fixture, coroutine factory) — each method must forward headers= verbatim.
HEADER_CASES = [
    ("get_item", "items/item_code_response.json",
     lambda c, h: c.get_item(ITEM_UUID, headers=h)),
    ("update_item_code", "items/item_code_update_response.json",
     lambda c, h: c.update_item_code(ITEM_UUID, "x", headers=h)),
    ("create_item", "items/item_create_response.json",
     lambda c, h: c.create_item(
         models.ItemCreateRequest(
             item_uuid=ITEM_UUID, item_sku="s", item_code=None, item_price=1,
             item_cost=0, order_uuid=ORDER_UUID, platform_name="p",
             platform_order_id="o", platform_item_id="i"),
         headers=h)),
    ("create_order", "orders/order_create_response.json",
     lambda c, h: c.create_order(
         models.OrderCreateRequest(
             order_uuid=ORDER_UUID, platform_name="p", platform_order_id="o",
             order_price=1, platform_fee_amount=0),
         headers=h)),
    ("get_order", "orders/order_response.json",
     lambda c, h: c.get_order(ORDER_UUID, headers=h)),
    ("get_order_items", "orders/order_items_response.json",
     lambda c, h: c.get_order_items(ORDER_UUID, headers=h)),
    ("create_slip", "slips/slip_create_response.json",
     lambda c, h: c.create_slip(
         models.SlipCreateRequest(item_sku="apple-1000", slip="aGVsbG8="), headers=h)),
    ("make_slip_actual", "slips/slip_actual_update_response.json",
     lambda c, h: c.make_slip_actual(SLIP_UUID, headers=h)),
    ("get_slip_by_uuid", "slips/slip_by_uuid_response.json",
     lambda c, h: c.get_slip_by_uuid(SLIP_UUID, headers=h)),
    ("get_slips", "slips/slips_list_response.json",
     lambda c, h: c.get_slips(headers=h)),
    ("get_slip_by_sku", "slips/slip_by_sku_response.json",
     lambda c, h: c.get_slip_by_sku("apple-1000", headers=h)),
]


@pytest.mark.parametrize("name, fixture, call", HEADER_CASES, ids=[c[0] for c in HEADER_CASES])
async def test_headers_propagated(mock_iris, load_fixture, name, fixture, call):
    mock_iris.respond_json(load_fixture(fixture))
    async with make_client() as client:
        await call(client, TRACE)

    sent = mock_iris.last_request
    for key, value in TRACE.items():
        assert sent.headers[key] == value
    # the static auth header is preserved alongside the per-request headers
    assert sent.headers["Authorization"] == f"Bearer {TOKEN}"


# --- error handling --------------------------------------------------------

async def test_non_2xx_raises_and_still_sends_trace(mock_iris, load_fixture):
    mock_iris.respond_json(load_fixture("errors/invalid_token_403.json"), status_code=403)
    async with make_client() as client:
        with pytest.raises(httpx.HTTPStatusError) as exc:
            await client.get_order(ORDER_UUID, headers=TRACE)

    assert exc.value.response.status_code == 403
    # trace headers were still attached to the failed request
    assert mock_iris.last_request.headers["X-Trace-Id"] == TRACE["X-Trace-Id"]


async def test_http_status_error_is_not_retried(mock_iris, load_fixture, fast_retry):
    # raise_for_status raises HTTPStatusError, which is not a RequestError, so
    # the tenacity retry must NOT kick in: exactly one request is made.
    mock_iris.respond_json(load_fixture("errors/invalid_token_403.json"), status_code=403)
    async with make_client() as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_order(ORDER_UUID)
    assert len(mock_iris.requests) == 1


async def test_network_error_retries_then_raises(mock_iris, fast_retry):
    # ConnectError is an httpx.RequestError -> retried up to 5 attempts. With
    # reraise=True (#20) the underlying httpx error surfaces directly, not
    # wrapped in tenacity.RetryError.
    mock_iris.fail(httpx.ConnectError("boom"))
    async with make_client() as client:
        with pytest.raises(httpx.ConnectError):
            await client.get_order(ORDER_UUID)
    assert len(mock_iris.requests) == 5
