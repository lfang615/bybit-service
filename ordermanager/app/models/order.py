from pydantic import BaseModel, Field, validator
from typing import Optional
from enum import Enum


class ExchangeID(str, Enum):
    BYBIT = "BYBIT"
    BITGET = "BITGET"
    BINANCE = "BINANCE"
    COINBASE = "COINBASE"

class FloatAsString(float):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        return float(value)
    
class OrderSide(str, Enum):
    BUY = "Buy"
    SELL = "Sell"

class OrderType(str, Enum):
    LIMIT = "Limit"
    MARKET = "Market"
    STOP_LIMIT = "StopLimit"
    STOP_MARKET = "StopMarket"
    TAKE_PROFIT_STOP_LOSS = "TPSL_Market"

class OrderStatus(str, Enum):
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

class TimeInForce(str, Enum):
    GTC = "GoodTillCancel"
    IOC = "ImmediateOrCancel"
    FOK = "FillOrKill"

class PositionAction(str, Enum):
    OPEN = "Open"
    CLOSE = "Close"
    
class Order(BaseModel):
    symbol: str
    side: OrderSide
    orderType: OrderType
    price: FloatAsString
    qty: FloatAsString
    orderLinkId: str
    orderId: str
    timeInForce: TimeInForce
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

    
    class Config:
        json_encoders = {
            OrderType: lambda x: x.value,
            OrderStatus: lambda x: x.value,
            OrderSide: lambda x: x.value,
            TimeInForce: lambda x: x.value,
        }

    def __eq__(self, other):
        if isinstance(other, Order):
            return (
                self.symbol == other.symbol
                and self.side == other.side
                and self.orderType == other.orderType
                and self.price == other.price
                and self.qty == other.qty
                and self.orderLinkId == other.orderLinkId
                and self.orderId == other.orderId
                and self.timeInForce == other.timeInForce
                and self.orderStatus == other.orderStatus
                and self.positionIdx == other.positionIdx
                and self.triggerBy == other.triggerBy
                and self.stopOrderType == other.stopOrderType
                and self.takeProfit == other.takeProfit
                and self.stopLoss == other.stopLoss
                and self.tpTriggerBy == other.tpTriggerBy
                and self.slTriggerBy == other.slTriggerBy
                and self.triggerPrice == other.triggerPrice
                and self.cancelType == other.cancelType
                and self.reduceOnly == other.reduceOnly
                and self.leavesQty == other.leavesQty
                and self.leavesValue == other.leavesValue
                and self.cumExecQty == other.cumExecQty
                and self.cumExecValue == other.cumExecValue
                and self.cumExecFee == other.cumExecFee
                and self.lastPriceOncreated == other.lastPriceOncreated
                and self.rejectReason == other.rejectReason
                and self.triggerDirection == other.triggerDirection
                and self.closeOnTrigger == other.closeOnTrigger
                and self.cancelType == other.cancelType
                and self.iv == other.iv
            )
        
    def __repr__(self):
        return (
            f"Order(symbol={self.symbol}, side={self.side}, orderType={self.orderType}, "
            f"price={self.price}, qty={self.qty}, orderLinkId={self.orderLinkId}, "
            f"orderId={self.orderId}, timeInForce={self.timeInForce}, "
            f"orderStatus={self.orderStatus}, positionIdx={self.positionIdx}, " 
            f"triggerBy={self.triggerBy}, stopOrderType={self.stopOrderType},"
            f"takeProfit={self.takeProfit}, stopLoss={self.stopLoss}, "
            f"tpTriggerBy={self.tpTriggerBy}, slTriggerBy={self.slTriggerBy}, "
            f"triggerPrice={self.triggerPrice}, cancelType={self.cancelType}, "
            f"reduceOnly={self.reduceOnly}, leavesQty={self.leavesQty}, "
            f"leavesValue={self.leavesValue}, cumExecQty={self.cumExecQty}, "
            f"cumExecValue={self.cumExecValue}, cumExecFee={self.cumExecFee}, "
            f"lastPriceOncreated={self.lastPriceOncreated}, "
            f"rejectReason={self.rejectReason}, "
            f"triggerDirection={self.triggerDirection}, "
            f"closeOnTrigger={self.closeOnTrigger}, "
            f"cancelType={self.cancelType}, iv={self.iv})"
        )

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
    orderType: OrderType
    qty: str
    price: Optional[str] = None
    timeInForce: TimeInForce
    triggerDirection: Optional[int] = None
    triggerPrice: Optional[str] = None  
    takeProfit: Optional[str] = None # ENTIRE POSITION WILL EXIT AT THIS PRICE
    stopLoss: Optional[str] = None # ENTIRE POSITION WILL EXIT AT THIS PRICE
    reduceOnly: Optional[bool] = None # When reduceOnly=True, takeProfit and stopLoss will be ignored
    closeOnTrigger: Optional[bool] = None
    positionIdx: Optional[int] = None

    class Config:
        json_encoders = {
            OrderType: lambda x: x.value,
            OrderStatus: lambda x: x.value,
            OrderSide: lambda x: x.value,
            TimeInForce: lambda x: x.value,
        }

    @validator("price", always=True)
    def validate_price(cls, price, values):
        order_type = values.get("orderType")
        if order_type == OrderType.LIMIT and price is None:
            raise ValueError("Price is required for Limit orders")
        if order_type == OrderType.MARKET and price is not None:
            raise ValueError("Price must not be set for Market orders")
        if order_type == OrderType.TAKE_PROFIT_STOP_LOSS and price is not None:
            raise ValueError("Only TriggerPrice is required for TAKE_PROFIT_STOP_LOSS orders")
        return price

    @validator("triggerPrice", always=True)
    def validate_trigger_price(cls, trigger_price, values):
        order_type = values.get("orderType")
        if order_type == OrderType.STOP_LIMIT and trigger_price is None:
            raise ValueError("TriggerPrice is required for StopLimit orders")
        if order_type == OrderType.STOP_MARKET and trigger_price is None:
            raise ValueError("TriggerPrice is required for StopMarket orders")
        return trigger_price

    @validator("takeProfit", "stopLoss", always=True)
    def validate_take_profit_stop_loss(cls, value, values):
        order_type = values.get("orderType")
        if order_type == OrderType.TAKE_PROFIT_STOP_LOSS and value is None:
            raise ValueError("TakeProfit and StopLoss are required for TPSL_Market orders")
        return value


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

class WalletBalanceRequest(BaseModel):
    depositAmt: Optional[float]
    withdrawAmt: Optional[float]
    currency: str = "USDT"
    
class WalletBalance(BaseModel):
    walletBalance: float
    positionBalance: float
    availableBalance: float
    currency: str = "USDT"


class RiskLimit(BaseModel):
    id: str
    symbol: str
    limit: str
    maintainMargin: float
    initialMargin: str
    isLowestRisk: int
    maxLeverage: str

class LeverageRequest(BaseModel):
    symbol: str
    buyLeverage: Optional[str] = None
    sellLeverage: Optional[str] = None

class LeverageResponse(BaseModel):
    symbol: str
    buyLeverage: Optional[str] = None
    sellLeverage: Optional[str] = None
    maxLeverage: str