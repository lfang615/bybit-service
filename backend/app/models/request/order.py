from pydantic import BaseModel
from typing import Optional
from models.data.order import Order
from enum import Enum

# enum of urls 
# class OrderType(str, Enum):
class BybitEndpoints(Enum):
    POSITION_INFO = "position/list"
    SET_LEVERAGE = "position/set-leverage"
    TP_SL = "position/set-tpsl-mode"
    TRADE_STOP = "position/trading-stop"
    

class OrderRequest(BaseModel):
    orderType: str
    qty: int
    takeProfit: Optional[float] = None
    stopLoss: Optional[float] = None
    triggerDirection: Optional[str] = None
    triggerPrice: Optional[float] = None

    # def to_order(self):
    #     return Order(
    #         orderType=self.orderType,
    #         qty=self.qty,
    #         takeProfit=self.takeProfit,
    #         stopLoss=self.stopLoss,
    #         triggerDirection=self.triggerDirection,
    #         triggerPrice=self.triggerPrice
    #     )