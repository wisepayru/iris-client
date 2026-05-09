from iris_client import Client
from iris_client import models


def test_client_import():
    assert Client is not None


def test_models_import():
    assert models.OrderCreateRequest is not None
    assert models.ItemCreateRequest is not None
    assert models.SlipCreateRequest is not None


def test_client_requires_token():
    try:
        Client(token="", base_url="http://localhost:8100")
        assert False, "Expected exception not raised"
    except ValueError:
        pass


def test_client_requires_base_url():
    try:
        Client(token="test-token", base_url="")
        assert False, "Expected exception not raised"
    except Exception:
        pass
