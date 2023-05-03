from pydantic import BaseModel, Field, validator
from typing import Optional
from enum import Enum


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


class OrderRequest(BaseModel):
    orderLinkId: str = Field(default="")
    symbol: str
    side: str
    orderType: str
    qty: str
    price: Optional[str] = None
    timeInForce: str
    triggerDirection: Optional[int] = None
    triggerPrice: Optional[str] = None  
    takeProfit: Optional[str] = None # ENTIRE POSITION WILL EXIT AT THIS PRICE
    stopLoss: Optional[str] = None # ENTIRE POSITION WILL EXIT AT THIS PRICE
    reduceOnly: Optional[bool] = None # When reduceOnly=True, takeProfit and stopLoss will be ignored
    closeOnTrigger: Optional[bool] = None


class EditOrderRequest(BaseModel):
    symbol: str
    orderLinkId: str
    price: Optional[str] = None # Don't pass if not modify price
    qty: Optional[str] = None # Don't pass if not modify qty
    triggerPrice: Optional[str] = None # Don't pass IF NOT MODIFY QUANTITY
    orderId: Optional[str] = None


class RetrieveOrdersRequest(BaseModel):
    orderStatus: str
    orderFilter: str

class CancelRequest(BaseModel):
    orderLinkId: str

class LeverageRequest(BaseModel):
    symbol: str
    buyLeverage: Optional[str] = None
    sellLeverage: Optional[str] = None

class WalletBalanceRequest(BaseModel):
    walletBallance: float
    

class WalletBalance(BaseModel):
    walletBalance: float
    positionBalance: float
    availableBalance: float

class RiskLimit(BaseModel):
    id: str
    symbol: str
    riskLimitValue: str
    maintenanceMargin: float
    initialMargin: str
    isLowestRiskLimit: int
    maxLeverage: str
