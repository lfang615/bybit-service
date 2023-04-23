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