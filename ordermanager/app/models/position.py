from pydantic import BaseModel
from typing import Optional
from ordermanager.app.models.order import Order

class Position(BaseModel):
    symbol: str
    side: str
    openDate: str
    qty: int
    aep: float
    linkedOrders: list[Order]
    closeDate: Optional[str] = None