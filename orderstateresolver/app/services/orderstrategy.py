from abc import ABC, abstractmethod
from orderstateresolver.app.models.order import OrderRequest, OrderSide, OrderType, PositionAction
import redis.asyncio as redis
from orderstateresolver.app.models.order import OrderRequest


class OrderStrategy(ABC):
    @staticmethod
    def order_builder_factory(self, order_request: OrderRequest, position_action: PositionAction) -> OrderRequest:
        builder = {
            PositionAction.OPEN: {
                OrderType.STOP_MARKET: self.build_open_stop_market_order,
                OrderType.STOP_LIMIT: self.build_open_stop_limit_order,
                OrderType.MARKET: self.build_open_market_order,
                OrderType.LIMIT: self.build_open_limit_order,
            },
            PositionAction.CLOSE: {
                OrderType.STOP_MARKET: self.build_close_stop_market_order,
                OrderType.TAKE_PROFIT_STOP_LOSS: self.build_close_tpsl_order,
                OrderType.STOP_LIMIT: self.build_close_stop_limit_order,
                OrderType.MARKET: self.build_close_market_order,
                OrderType.LIMIT: self.build_close_limit_order,
            },
        }
        return builder[position_action][order_request.orderType](order_request)

    @abstractmethod
    def build_open_limit_order(self, order_request: OrderRequest):
        pass

    @abstractmethod
    def build_open_market_order(self, order_request: OrderRequest):
        pass

    @abstractmethod
    def build_open_stop_market_order(self, order_request: OrderRequest):
        pass

    @abstractmethod
    def build_open_stop_limit_order(self, order_request: OrderRequest):
        pass

    @abstractmethod
    def build_close_limit_order(self, order_request: OrderRequest):
        pass

    @abstractmethod
    def build_close_market_order(self, order_request: OrderRequest):
        pass

    @abstractmethod
    def build_close_stop_market_order(self, order_request: OrderRequest):
        pass

    @abstractmethod
    def build_close_stop_limit_order(self, order_request: OrderRequest):
        pass

    @abstractmethod
    def build_tpsl_order(self, order_request: OrderRequest):
        pass
