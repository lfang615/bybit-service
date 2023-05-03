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
    
    def __eq__(self, other):
        if not isinstance(other, Order):
            return NotImplemented
        return (self.symbol == other.symbol and
                self.side == other.side and
                self.orderType == other.orderType and
                self.price == other.price and
                self.qty == other.qty and
                self.orderLinkId == other.orderLinkId and
                self.orderId == other.orderId and
                self.timeInForce == other.timeInForce and
                self.orderStatus == other.orderStatus and
                self.positionIdx == other.positionIdx and
                self.triggerBy == other.triggerBy and
                self.stopOrderType == other.stopOrderType and
                self.takeProfit == other.takeProfit and
                self.stopLoss == other.stopLoss and
                self.tpTriggerBy == other.tpTriggerBy and
                self.slTriggerBy == other.slTriggerBy and
                self.triggerPrice == other.triggerPrice and
                self.cancelType == other.cancelType and
                self.reduceOnly == other.reduceOnly and
                self.leavesQty == other.leavesQty and
                self.leavesValue == other.leavesValue and
                self.cumExecQty == other.cumExecQty and
                self.cumExecValue == other.cumExecValue and
                self.cumExecFee == other.cumExecFee and
                self.lastPriceOncreated == other.lastPriceOncreated and
                self.rejectReason == other.rejectReason and
                self.triggerDirection == other.triggerDirection and
                self.closeOnTrigger == other.closeOnTrigger and
                self.cancelType == other.cancelType and
                self.iv == other.iv)