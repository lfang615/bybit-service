from ordermanager.app.models.order import OrderRequest, OrderType, OrderSide, ExchangeID, PositionAction
from ordermanager.app.models.position import Position
from ordermanager.app.exceptions import InvalidOrderTypeException
from ordermanager.app.utils import opposite_side
from ordermanager.app.services.orderstrategy import OrderStrategy
import asyncio
import redis.asyncio as redis
import json


class BybitOrderStrategy(OrderStrategy):
    
    @staticmethod
    def build_open_limit_order(order_request: OrderRequest):
        """
        Open Long - price must be below the current market price
        Open Short - price must be above the current market price
        """
        limit_order_request = OrderRequest(
            symbol=order_request.symbol,
            reduceOnly=False,
            side=order_request.side,
            orderType=OrderType.LIMIT.value,
            qty=order_request.qty,
            price=order_request.price,
            timeInForce=order_request.timeInForce
        )
        return limit_order_request
    
    @staticmethod
    def build_close_limit_order(order_request: OrderRequest):
        """
        Close Long - price must be above the current market price
        Close Short - price must be below the current market price
        """
        limit_order_request = OrderRequest(
            symbol=order_request.symbol,
            reduceOnly=True,
            side=order_request.side,
            orderType=OrderType.LIMIT.value,
            qty=order_request.qty,
            price=order_request.price,
            positionIdx=1 if order_request.side == OrderSide.BUY.value else 2,
            timeInForce=order_request.timeInForce
        )
        return limit_order_request
    
    @staticmethod
    def build_open_market_order(order_request: OrderRequest):
        market_order_request = OrderRequest(
            symbol=order_request.symbol,
            reduceOnly=False,
            side=order_request.side,
            orderType=OrderType.MARKET.value,
            qty=order_request.qty,
            timeInForce=order_request.timeInForce
        )
        return market_order_request
    
    @staticmethod
    def build_close_market_order(order_request: OrderRequest):
        """
        Used to close a position immediately at the best available price 
        """
        market_order_request = OrderRequest(
            symbol=order_request.symbol,
            reduceOnly=True,
            side=order_request.side,
            orderType=OrderType.MARKET.value,
            qty=order_request.qty,
            positionIdx=1 if order_request.side == OrderSide.BUY.value else 2,
            closeOnTrigger=True,
            timeInForce=order_request.timeInForce
        )
        return market_order_request
    
    @staticmethod
    def build_open_stop_market_order(order_request: OrderRequest):
        """
        Buy stop (Long) orders are triggered when the last traded price in the market is equal to or higher than the trigger price of the order.
        The order is then executed at the best available price in the market.
        Sell stop (Short) orders are triggered when the last traded price in the market is equal to or lower than the trigger price of the order.
        """
        stop_market_order_request = OrderRequest(
            symbol=order_request.symbol,
            reduceOnly=False,
            side=order_request.side,
            orderType=OrderType.MARKET.value,
            qty=order_request.qty,
            triggerPrice=order_request.triggerPrice,
            triggerDirection=1 if order_request.side == OrderSide.BUY.value else 2,
            timeInForce=order_request.timeInForce
        )
        return stop_market_order_request
    
    @staticmethod
    def build_close_stop_market_order(order_request: OrderRequest):
        """
        Buy stop (Use as stop loss for Shorts) orders are triggered when the last traded price in the market is equal to or higher than the trigger price of the order.
        Sell stop (Use as stop loss for Longs) orders are triggered when the last traded price in the market is equal to or lower than the trigger price of the order.
        """
        stop_market_order_request = OrderRequest(
            symbol=order_request.symbol,
            reduceOnly=True,
            side=order_request.side,
            orderType=OrderType.MARKET.value,
            qty=order_request.qty,
            triggerPrice=order_request.triggerPrice,
            triggerDirection=1 if order_request.side == OrderSide.BUY.value else 2,
            positionIdx=1 if order_request.side == OrderSide.BUY.value else 2,
            timeInForce=order_request.timeInForce
        )
        return stop_market_order_request
    
    @staticmethod
    def build_tpsl_order(order_request: OrderRequest):
        """
        Same as stop market order except that entire qty of position will be closed 
        without the need to specify the qty
        """
        pass
    
    @staticmethod
    def build_open_stop_limit_order(order_request: OrderRequest):
        """
        Sell limit orders (Open Short) are opened when the trigger price is above the last traded price in the market.
        Buy limit orders (Open Long) are opened when the trigger price is below the last traded price in the market.
        """
        stop_limit_order_request = OrderRequest(
            symbol=order_request.symbol,
            price=order_request.price,
            reduceOnly=False,
            side=order_request.side,
            orderType=OrderType.LIMIT.value,
            qty=order_request.qty,
            triggerPrice=order_request.triggerPrice,
            triggerDirection=1 if order_request.side == OrderSide.BUY.value else 2,
            timeInForce=order_request.timeInForce
        )
        return stop_limit_order_request
    
    @staticmethod
    def build_close_stop_limit_order(order_request: OrderRequest):
        """
        Sell limit orders (Close Long) are opened when the trigger price is above the last traded price in the market.
        Buy limit orders (Close Short) are opened when the trigger price is below the last traded price in the market.
        """
        stop_limit_order_request = OrderRequest(
            symbol=order_request.symbol,
            price=order_request.price,
            reduceOnly=True,
            side=order_request.side,
            orderType=OrderType.LIMIT.value,
            qty=order_request.qty,
            triggerPrice=order_request.triggerPrice,
            triggerDirection=1 if order_request.side == OrderSide.BUY.value else 2,
            positionIdx=1 if order_request.side == OrderSide.BUY.value else 2,
            closeOnTrigger=True,
            timeInForce=order_request.timeInForce
        )
        return stop_limit_order_request
    


        
   