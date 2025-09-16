import os
import httpx
from typing import Optional, Tuple
from uuid import UUID
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
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

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(httpx.RequestError)
    )
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
