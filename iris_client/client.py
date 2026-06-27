import httpx
from importlib.metadata import version, PackageNotFoundError
from typing import Dict, Optional, Tuple, List
from uuid import UUID
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from . import models

try:
    _version = version("iris-client")
except PackageNotFoundError:
    _version = "dev"

_USER_AGENT = f"wisepay-iris-client/{_version}"

class Client:
    def __init__(self, token: str, base_url: str):
        if not token:
            raise ValueError("Iris API token is required.")
        if not base_url:
            raise ValueError("Iris base_url is required.")
        self.base_url = base_url
        self._token = token
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT
        }
        self._client = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=httpx.Timeout(10.0, connect=5.0)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        # Re-raise the underlying httpx error on exhaustion instead of wrapping
        # it in tenacity.RetryError, so consumers can catch httpx exceptions
        # directly (#20).
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        url: str,
        extra_headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Tuple[httpx.Request, httpx.Response, dict]:
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with Client(...)'.")
        if extra_headers:
            kwargs["headers"] = {**kwargs.pop("headers", {}), **extra_headers}
        req = self._client.build_request(method, url, **kwargs)
        resp = await self._client.send(req)
        resp.raise_for_status()
        return req, resp, resp.json()

    async def get_item(
        self,
        item_uuid: UUID,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[httpx.Request, httpx.Response, models.ItemCodeResponse]:
        req, resp, data = await self._request("GET", f"/item/{item_uuid}", extra_headers=headers)
        return req, resp, models.ItemCodeResponse.model_validate(data)

    async def update_item_code(
        self,
        item_uuid: UUID,
        item_code: Optional[str],
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[httpx.Request, httpx.Response, models.ItemCodeUpdateResponse]:
        payload = models.ItemCodeUpdateRequest(item_code=item_code)
        req, resp, data = await self._request(
            "PUT", f"/item/{item_uuid}/code", json=payload.model_dump(), extra_headers=headers
        )
        return req, resp, models.ItemCodeUpdateResponse.model_validate(data)

    async def create_item(
        self,
        item_data: models.ItemCreateRequest,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[httpx.Request, httpx.Response, models.ItemCreateResponse]:
        req, resp, data = await self._request(
            "POST", "/item", json=item_data.model_dump(mode='json'), extra_headers=headers
        )
        return req, resp, models.ItemCreateResponse.model_validate(data)

    async def create_order(
        self,
        order_data: models.OrderCreateRequest,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[httpx.Request, httpx.Response, models.OrderCreateResponse]:
        req, resp, data = await self._request(
            "POST", "/order", json=order_data.model_dump(mode='json'), extra_headers=headers
        )
        return req, resp, models.OrderCreateResponse.model_validate(data)

    async def get_order(
        self,
        order_uuid: UUID,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[httpx.Request, httpx.Response, models.OrderResponse]:
        req, resp, data = await self._request("GET", f"/order/{order_uuid}", extra_headers=headers)
        return req, resp, models.OrderResponse.model_validate(data)

    async def get_order_items(
        self,
        order_uuid: UUID,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[httpx.Request, httpx.Response, models.OrderItemsResponse]:
        req, resp, data = await self._request(
            "GET", f"/order/{order_uuid}/items", extra_headers=headers
        )
        return req, resp, models.OrderItemsResponse.model_validate(data)

    async def create_slip(
        self,
        slip_data: models.SlipCreateRequest,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[httpx.Request, httpx.Response, models.SlipCreateResponse]:
        req, resp, data = await self._request(
            "POST", "/slip", json=slip_data.model_dump(mode='json'), extra_headers=headers
        )
        return req, resp, models.SlipCreateResponse.model_validate(data)

    async def make_slip_actual(
        self,
        slip_uuid: UUID,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[httpx.Request, httpx.Response, models.SlipActualUpdateResponse]:
        req, resp, data = await self._request(
            "POST", f"/slip/{slip_uuid}/makeActual", extra_headers=headers
        )
        return req, resp, models.SlipActualUpdateResponse.model_validate(data)

    async def get_slip_by_uuid(
        self,
        slip_uuid: UUID,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[httpx.Request, httpx.Response, models.SlipByUuidResponse]:
        req, resp, data = await self._request("GET", f"/slip/{slip_uuid}", extra_headers=headers)
        return req, resp, models.SlipByUuidResponse.model_validate(data)

    async def get_slips(
        self,
        sku: Optional[str] = None,
        only_actual: bool = True,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[httpx.Request, httpx.Response, List[models.SlipByUuidResponse]]:
        # Always send onlyActual: omitting it on False let the server fall back
        # to its onlyActual=True default, so non-actual slips were unreachable
        # (#14). httpx serialises the bool to "true"/"false".
        params = {'onlyActual': only_actual}
        if sku:
            params['sku'] = sku
        req, resp, data = await self._request("GET", "/slips", params=params, extra_headers=headers)
        return req, resp, [models.SlipByUuidResponse.model_validate(s) for s in data]

    async def get_slip_by_sku(
        self,
        item_sku: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[httpx.Request, httpx.Response, models.SlipBySkuResponse]:
        req, resp, data = await self._request(
            "GET", f"/sku/{item_sku}/slip", extra_headers=headers
        )
        return req, resp, models.SlipBySkuResponse.model_validate(data)
