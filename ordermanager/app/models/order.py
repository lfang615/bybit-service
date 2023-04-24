from pydantic import BaseModel
from typing import Optional
from enum import Enum

    
class Order(BaseModel):
    symbol: str
    side: str
    orderType: str
    price: str
    qty: str
    orderLinkId: str
    orderId: str
    timeInForce: str
    orderStatus: Optional[str]
    positionIdx: Optional[str]
    triggerBy: Optional[str]
    stopOrderType:Optional[str]
    takeProfit: Optional[str]
    stopLoss: Optional[str]
    tpTriggerBy: Optional[str]
    slTriggerBy: Optional[str]
    triggerPrice: Optional[str]
    cancelType: Optional[str]
    reduceOnly: Optional[str]
    leavesQty: Optional[str]
    leavesValue: Optional[str]
    cumExecQty: Optional[str]
    cumExecValue: Optional[str]
    cumExecFee: Optional[str]
    lastPriceOncreated: Optional[str]
    rejectReason: Optional[str]
    triggerDirection: Optional[str]
    closeOnTrigger: Optional[str]
    cancelType: Optional[str]
    iv: Optional[str] # Implied Volatility

    
class OrderRequest(BaseModel):
    orderLinkId: str = None
    symbol: str
    side: str
    orderType: str
    qty: str
    price: Optional[str] = None
    triggerDirection: Optional[int] = None
    triggerPrice: Optional[str] = None
    timeInForce: str
    positionIdx: Optional[int]
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
    walletBallance: float
    positionBalance: float
    availableBalance: float

class RiskLimits(BaseModel):
    id: str
    symbol: str
    riskLimitValue: str
    maintenaceMargin: str
    initialMargin: str
    isLowestRiskLimit: int
    maxLeverage: str
