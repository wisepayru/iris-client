"""Unit tests for iris_client.models.

Two concerns: (1) the parsing edge cases that are easy to regress — the
``uuid`` alias, tz-aware timestamps, optional ``item_code``, json-mode dumping;
(2) a contract-drift guard that validates every response model against a
captured/spec-derived fixture, so the client and the ``iris`` service can't
silently diverge (see tests/fixtures/README.md for provenance).
"""

import datetime
from uuid import UUID

import pytest

from iris_client import models

SLIP_UUID = UUID("33dbf274-4c1c-4287-a774-31f6d70d16af")


# --- parsing edge cases ----------------------------------------------------

def test_slip_by_uuid_alias_and_timestamps(load_fixture):
    body = load_fixture("slips/slip_by_uuid_response.json")
    parsed = models.SlipByUuidResponse.model_validate(body)

    # the wire key is "uuid"; the model maps it to slip_uuid via the alias
    assert "uuid" in body and "slip_uuid" not in body
    assert parsed.slip_uuid == SLIP_UUID
    # Moscow-tz isoformat string parsed into a tz-aware datetime
    assert isinstance(parsed.created_dttm, datetime.datetime)
    assert parsed.created_dttm.utcoffset() == datetime.timedelta(hours=3)


def test_slip_by_uuid_requires_alias_key():
    # Without the "uuid" alias key, validation fails (alias is required).
    with pytest.raises(Exception):
        models.SlipByUuidResponse.model_validate({
            "slip_uuid": str(SLIP_UUID),
            "item_sku": "apple-1000",
            "slip": "aGVsbG8=",
            "actual_flg": True,
            "created_dttm": "2026-06-13T13:21:54+03:00",
            "updated_dttm": "2026-06-13T13:21:54+03:00",
        })


def test_item_code_response_optional_code(load_fixture):
    body = dict(load_fixture("items/item_code_response.json"))
    body["item_code"] = None
    parsed = models.ItemCodeResponse.model_validate(body)
    assert parsed.item_code is None


def test_item_create_request_json_dump_serializes_uuids():
    item = models.ItemCreateRequest(
        item_uuid=SLIP_UUID,
        item_sku="apple-1000",
        item_code=None,
        item_price=10.5,
        item_cost=0,
        order_uuid=UUID("7eb92490-d4e7-4141-8af0-1510e8867ef2"),
        platform_name="YANDEX_MARKET",
        platform_order_id="o",
        platform_item_id="i",
    )
    dumped = item.model_dump(mode="json")
    assert dumped["item_uuid"] == str(SLIP_UUID)
    assert dumped["order_uuid"] == "7eb92490-d4e7-4141-8af0-1510e8867ef2"
    assert dumped["item_code"] is None


def test_slip_create_response_nested_data(load_fixture):
    parsed = models.SlipCreateResponse.model_validate(
        load_fixture("slips/slip_create_response.json"))
    assert parsed.message == "Slip created successfully"
    assert isinstance(parsed.data, models.SlipResponse)
    assert parsed.data.slip_uuid == SLIP_UUID
    assert parsed.data.actual_flg is False


# --- contract-drift guard --------------------------------------------------

# Each response model must parse the captured/spec-derived body for its
# endpoint. If the iris service changes a response shape, regenerate the
# fixture and this flags the divergence.
RESPONSE_CONTRACTS = [
    ("orders/order_create_response.json", models.OrderCreateResponse),
    ("orders/order_response.json", models.OrderResponse),
    ("orders/order_items_response.json", models.OrderItemsResponse),
    ("items/item_create_response.json", models.ItemCreateResponse),
    ("items/item_code_response.json", models.ItemCodeResponse),
    ("items/item_code_update_response.json", models.ItemCodeUpdateResponse),
    ("slips/slip_by_sku_response.json", models.SlipBySkuResponse),
    ("slips/slip_create_response.json", models.SlipCreateResponse),
    ("slips/slip_actual_update_response.json", models.SlipActualUpdateResponse),
    ("slips/slip_by_uuid_response.json", models.SlipByUuidResponse),
]


@pytest.mark.parametrize("fixture, model", RESPONSE_CONTRACTS, ids=[c[0] for c in RESPONSE_CONTRACTS])
def test_response_model_matches_fixture(load_fixture, fixture, model):
    model.model_validate(load_fixture(fixture))


def test_slips_list_contract(load_fixture):
    body = load_fixture("slips/slips_list_response.json")
    parsed = [models.SlipByUuidResponse.model_validate(s) for s in body]
    assert len(parsed) == 2
    assert all(isinstance(s, models.SlipByUuidResponse) for s in parsed)
