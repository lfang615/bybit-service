from pydantic import BaseModel
from typing import Optional
from enum import Enum

    
class Order(BaseModel):
    symbol: str
    side: str
    orderType: str
    qty: str
    price: str
    timeInForce: str
    positionIdx: Optional[int]
    takeProfit: Optional[str] = None
    stopLoss: Optional[str] = None
    orderId: str
    lastPriceOncreated: Optional[str] = None # last price when order was created
    createdTime: Optional[str] = None # time order was created on Bybit's server
    updatedTime: Optional[str] = None # time order was updated on Bybit's server
    reduceOnly: Optional[bool] = None
    avgEntryPrice: Optional[str] = None
    avgExitPrice: Optional[str] = None
    closedPnL: Optional[str] = None
    cumExecQty: Optional[str] = None

    
class OrderRequest(BaseModel):
    symbol: str
    side: str
    orderType: str
    qty: str
    price: str
    timeInForce: str
    positionIdx: Optional[int]
    takeProfit: Optional[str] = None
    stopLoss: Optional[str] = None
    orderId: str = None    
    reduceOnly: Optional[bool] = None

class RetrieveOrdersRequest(BaseModel):
    orderStatus: str
    orderFilter: str

class CancelRequest(BaseModel):
    orderId: str