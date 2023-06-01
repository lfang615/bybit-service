from orderstateresolver.app.models.order import OrderRequest, OrderType, OrderSide, ExchangeID, PositionAction, PlaceOrderStructure, BitgetStopOrder, BitgetTPSLOrder
from orderstateresolver.app.models.position import Position
from orderstateresolver.app.exceptions import InvalidOrderTypeException
from orderstateresolver.app.utils import opposite_side
from orderstateresolver.app.services.abstractexchange import AbstractExchange
import ccxt.async_support as ccxt
from ccxt import NetworkError, ExchangeError
import asyncio
import redis.asyncio as redis
from pydantic import BaseModel, ValidationError
from typing import Coroutine, Type, Dict, Any, Union
import json
import logging



class BitgetOrderStrategy(AbstractExchange):
    def __init__(self, exchange_id: ExchangeID, **kwargs):
        super().__init__(exchange_id, **kwargs)


    async def create_stop_limit_order(self, order_request:PlaceOrderStructure, **kwargs):
        try:                
            BitgetStopOrder(**kwargs)
            order = await self.exchange.create_order(order = await self.exchange.create_order(symbol=None, type=None, side=None, amount=None, price=None, params=kwargs))
            return order
        except ValidationError as e:
            logging.error(f"Invalid BitgetStopOrder: {e}")
            raise ValueError(f"Invalid BitgetStopOrder: {e}")
        except Exception as e:
            logging.error(f"Error creating order: {e}")
            raise e


    async def create_stop_market_order(self, order_request:PlaceOrderStructure, **kwargs):
        try:           
            BitgetStopOrder(**kwargs)     
            order = await self.exchange.create_order(symbol=None, type=None, side=None, amount=None, price=None, params=kwargs)
            return order
        except ValidationError as e:
            logging.error(f"Invalid BitgetStopOrder: {e}")
            raise ValueError(f"Invalid BitgetStopOrder: {e}")
        except Exception as e:
            logging.error(f"Error creating order: {e}")


    async def create_tpsl_order(self, order_request:PlaceOrderStructure, **kwargs):
        try:                
            BitgetTPSLOrder(**kwargs)
            order = await self.exchange.create_order(symbol=None, type=None, side=None, amount=None, price=None, params=kwargs)
            return order
        except ValidationError as e:
            logging.error(f"Invalid BitgetTPSLOrder: {e}")
            raise ValueError(f"Invalid BitgetTPSLOrder: {e}")
        except Exception as e:
            logging.error(f"Error creating order: {e}")


