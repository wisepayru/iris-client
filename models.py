from pydantic import BaseModel, UUID4
from typing import Optional, List, Dict, Any

class OrderResponse(BaseModel):
    order_uuid: UUID4
    platform_name: str
    platform_order_id: str
    order_price: float
    platform_fee_amount: float

class OrderItemsResponse(BaseModel):
    order_uuid: UUID4
    items: List[Dict[str, Any]]

class ItemCodeResponse(BaseModel):
    item_uuid: UUID4
    item_sku: str
    item_code: Optional[str] = None
    item_price: float
    item_cost: float
    order_uuid: UUID4
    platform_name: str
    platform_order_id: str
    platform_item_id: str

class ItemCodeUpdateResponse(BaseModel):
    message: str
    item_uuid: UUID4
    platform_item_id: str
    item_sku: str
    item_code: Optional[str] = None

class ItemCodeUpdateRequest(BaseModel):
    item_code: Optional[str] = None

class ItemCreateRequest(BaseModel):
    item_uuid: UUID4
    item_sku: str
    item_code: Optional[str] = None
    item_price: float
    item_cost: float
    order_uuid: UUID4
    platform_name: str
    platform_order_id: str
    platform_item_id: str

class ItemCreateResponse(BaseModel):
    message: str
    item_uuid: UUID4
    item_sku: str
    item_code: Optional[str] = None
    item_price: float
    item_cost: float
    order_uuid: UUID4
    platform_name: str
    platform_order_id: str
    platform_item_id: str

class OrderCreateRequest(BaseModel):
    order_uuid: UUID4
    platform_name: str
    platform_order_id: str
    order_price: float
    platform_fee_amount: float

class OrderCreateResponse(BaseModel):
    message: str
    order_uuid: UUID4
    platform_name: str
    platform_order_id: str
    order_price: float
    platform_fee_amount: float
