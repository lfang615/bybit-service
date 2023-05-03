from pydantic import BaseModel, validator
from typing import Optional
from enum import Enum


class FloatAsString(float):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        return float(value)
    
class OrderSide(Enum):
    BUY = "Buy"
    SELL = "Sell"

class OrderType(Enum):
    LIMIT = "Limit"
    MARKET = "Market"
    STOP_LIMIT = "StopLimit"
    TAKE_PROFIT_LIMIT = "TakeProfit"
    STOP_MARKET = "StopMarket"
    TAKE_PROFIT_MARKET = "TakeProfitMarket"
    TRAILING_STOP_MARKET = "TrailingStopMarket"

class OrderStatus(Enum):
    PENDING = "Pending" # This is a custom status
    NEW = "New"
    PARTIALLY_FILLED = "PartiallyFilled"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"
    DEACTIVATED = "Deactivated"
    ACTIVE = "Active"
    TRIGGERED = "Triggered"
    PENDINGCANCEL = "PendingCancel"
    UNTRIGGERED = "Untriggered"
    CREATED = "Created"
    
class Order(BaseModel):
    symbol: str
    side: OrderSide
    orderType: OrderType
    price: FloatAsString
    qty: FloatAsString
    orderLinkId: str
    orderId: str
    timeInForce: str
    orderStatus: Optional[OrderStatus]
    positionIdx: Optional[str]
    triggerBy: Optional[str]
    stopOrderType:Optional[str]
    takeProfit: Optional[FloatAsString]
    stopLoss: Optional[FloatAsString]
    tpTriggerBy: Optional[str]
    slTriggerBy: Optional[str]
    triggerPrice: Optional[FloatAsString]
    cancelType: Optional[str]
    reduceOnly: Optional[str]
    leavesQty: Optional[FloatAsString]
    leavesValue: Optional[FloatAsString]
    cumExecQty: Optional[FloatAsString]
    cumExecValue: Optional[FloatAsString]
    cumExecFee: Optional[FloatAsString]
    lastPriceOncreated: Optional[FloatAsString]
    rejectReason: Optional[str]
    triggerDirection: Optional[str]
    closeOnTrigger: Optional[str]
    cancelType: Optional[str]
    iv: Optional[str] # Implied Volatility

    @validator("reduceOnly", pre=False)
    def str_to_bool(cls, value):
        if isinstance(value, str) and value.lower() == "true":
            return True
        elif isinstance(value, str) and value.lower() == "false":
            return False
        return bool(value)