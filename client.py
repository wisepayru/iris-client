import os
import httpx
from typing import Optional, Tuple
from uuid import UUID
from . import models

class Client:
    """
    Asynchronous client for interacting with the Iris API.
    """
    def __init__(self, token: str, base_url: str = "http://localhost:8000"):
        if not token:
            raise ValueError("Iris API token is required.")
        self.base_url = base_url
        self._token = token
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "User-Agent": "github:wisepay/ym-api"
        }
        self._client = None

    async def __aenter__(self):
        """
        Initializes the httpx.AsyncClient.
        """
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=httpx.Timeout(10.0, connect=5.0)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Closes the httpx.AsyncClient.
        """
        if self._client:
            await self._client.aclose()

    async def _request(self, method: str, url: str, **kwargs) -> Tuple[httpx.Request, httpx.Response, dict]:
        """
        Helper method to make a request and handle responses.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with Client(...)'.")
        
        req = self._client.build_request(method, url, **kwargs)
        resp = await self._client.send(req)
        
        resp.raise_for_status() # Raise an exception for 4xx or 5xx status codes
        
        return req, resp, resp.json()

    async def get_item(self, item_uuid: UUID) -> Tuple[httpx.Request, httpx.Response, models.ItemCodeResponse]:
        """
        Retrieve item code details for a given item UUID.
        """
        req, resp, data = await self._request("GET", f"/item/{item_uuid}")
        return req, resp, models.ItemCodeResponse.model_validate(data)

    async def update_item_code(self, item_uuid: UUID, item_code: Optional[str]) -> Tuple[httpx.Request, httpx.Response, models.ItemCodeUpdateResponse]:
        """
        Updates the item code for a specific item.
        """
        payload = models.ItemCodeUpdateRequest(item_code=item_code)
        req, resp, data = await self._request("PUT", f"/item/{item_uuid}/code", json=payload.model_dump())
        return req, resp, models.ItemCodeUpdateResponse.model_validate(data)

    async def create_item(self, item_data: models.ItemCreateRequest) -> Tuple[httpx.Request, httpx.Response, models.ItemCreateResponse]:
        """
        Creates a new item.
        """
        req, resp, data = await self._request("POST", "/item", json=item_data.model_dump(mode='json'))
        return req, resp, models.ItemCreateResponse.model_validate(data)

    async def create_order(self, order_data: models.OrderCreateRequest) -> Tuple[httpx.Request, httpx.Response, models.OrderCreateResponse]:
        """
        Creates a new order.
        """
        req, resp, data = await self._request("POST", "/order", json=order_data.model_dump(mode='json'))
        return req, resp, models.OrderCreateResponse.model_validate(data)

    async def get_order(self, order_uuid: UUID) -> Tuple[httpx.Request, httpx.Response, models.OrderResponse]:
        """
        Retrieve an order by its UUID.
        """
        req, resp, data = await self._request("GET", f"/order/{order_uuid}")
        return req, resp, models.OrderResponse.model_validate(data)

    async def get_order_items(self, order_uuid: UUID) -> Tuple[httpx.Request, httpx.Response, models.OrderItemsResponse]:
        """
        Retrieve all items associated with a specific order.
        """
        req, resp, data = await self._request("GET", f"/order/{order_uuid}/items")
        return req, resp, models.OrderItemsResponse.model_validate(data)

    async def create_slip(self, slip_data: models.SlipCreateRequest) -> Tuple[httpx.Request, httpx.Response, models.SlipCreateResponse]:
        """
        Creates a new slip.
        """
        req, resp, data = await self._request("POST", "/slip", json=slip_data.model_dump(mode='json'))
        return req, resp, models.SlipCreateResponse.model_validate(data)

    async def make_slip_actual(self, slip_uuid: UUID) -> Tuple[httpx.Request, httpx.Response, models.SlipActualUpdateResponse]:
        """
        Sets a specific slip as the actual one.
        """
        req, resp, data = await self._request("POST", f"/slip/{slip_uuid}/makeActual")
        return req, resp, models.SlipActualUpdateResponse.model_validate(data)

    async def get_slip_by_uuid(self, slip_uuid: UUID) -> Tuple[httpx.Request, httpx.Response, models.SlipByUuidResponse]:
        """
        Retrieve slip data by its UUID.
        """
        req, resp, data = await self._request("GET", f"/slip/{slip_uuid}")
        return req, resp, models.SlipByUuidResponse.model_validate(data)

    async def get_slips(self, sku: Optional[str] = None, only_actual: bool = True) -> Tuple[httpx.Request, httpx.Response, list[models.SlipByUuidResponse]]:
        """
        Retrieve a list of slips, with optional filtering.
        """
        params = {}
        if sku:
            params['sku'] = sku
        if only_actual:
            params['onlyActual'] = only_actual
        
        req, resp, data = await self._request("GET", "/slips", params=params)
        
        # Assuming the response is a list of slip objects
        validated_slips = [models.SlipByUuidResponse.model_validate(slip_data) for slip_data in data]
        
        return req, resp, validated_slips

    async def get_slip_by_sku(self, item_sku: str) -> Tuple[httpx.Request, httpx.Response, models.SlipBySkuResponse]:
        """
        Retrieve the actual slip for a given item_sku.
        """
        req, resp, data = await self._request("GET", f"/sku/{item_sku}/slip")
        return req, resp, models.SlipBySkuResponse.model_validate(data)
