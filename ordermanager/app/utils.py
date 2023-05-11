import logging
from ordermanager.app.models.order import OrderRequest, WalletBalance, RiskLimit, OrderSide, ExchangeID
from ordermanager.app.models.position import Position
import json
from ordermanager.app.exceptions import CachedDataException, InvalidOrderTypeException
import redis.asyncio as redis


def calculate_order_cost(order_request: OrderRequest, max_leverage: str) -> float:
    price = float(order_request.price)
    qty = float(order_request.qty)
    max_leverage = float(max_leverage)

    initial_margin = (price * qty) / max_leverage
    fee_to_open_position = qty * price * 0.0006

    if order_request.side == "Buy":
        bankruptcy_price = (price * qty) * (1 - (1 / max_leverage))
    elif order_request.side == "Sell":
        bankruptcy_price = (price * qty) * (1 + (1 / max_leverage))

    fee_to_close_position = qty * bankruptcy_price * 0.0006

    return initial_margin + fee_to_open_position + fee_to_close_position


async def update_wallet_balance(wallet_balance: WalletBalance, redis: redis.Redis, exchange_id: ExchangeID):
    try:
        wallet_balance_key = "wallet_balance"
        await set_cache_value(wallet_balance_key, wallet_balance.dict(), redis, exchange_id)
        return True
    except Exception as e:
        logging.error(f"Error update_wallet_balance, {e}")
        raise e


async def get_wallet_balance(redis: redis.Redis, exchange_id: ExchangeID) -> WalletBalance:
    try:
        wallet_balance_data = await get_cache_value("wallet_balance", redis, exchange_id)
        if wallet_balance_data:
            wallet_balance = WalletBalance(**json.loads(wallet_balance_data))
            return wallet_balance
        else:
            return WalletBalance()
    except Exception as e:
        logging.error("Error get_wallet_balance, {e}")
        return {"error": str(e)}


async def get_risk_limits_for_symbol(symbol:str, redis: redis.Redis, exchange_id: ExchangeID) -> RiskLimit:
    try:
        risk_limit_data = await get_cache_value(f"risk_limits:{symbol}", redis, exchange_id)
        if risk_limit_data:
            risk_limits = RiskLimit(**json.loads(risk_limit_data))
            return risk_limits
        else:
            raise CachedDataException("No cached data for risk limits")
    except Exception as e:
        logging.error("Error get_risk_limits_for_symbol, {e}")
        return {"error": str(e)}
    

async def get_cache_value(key: str, redis: redis.Redis, exchange_id: ExchangeID):
    try:
        modified_key = f"{exchange_id}:{key}"
        data = await redis.get(modified_key)
        if data:
            return data
        else:
            return None
    except Exception as e:
        logging.error(f"Error get_from_redis_cache, {e}")
        raise e
    
async def set_cache_value(key: str, data: dict, redis: redis.Redis, exchange_id: ExchangeID):
    try:        
        modified_key = f"{exchange_id}:{key}"
        await redis.set(modified_key, json.dumps(data))
    except Exception as e:
        logging.error(f"Error set_cache_value, {e}")
        raise e
    
def opposite_side(side: OrderSide) -> OrderSide:
    if side == OrderSide.BUY.value:
        return OrderSide.SELL.value
    else:
        return OrderSide.BUY.value

async def validate_closing_position(order_request: OrderRequest, redis: redis.Redis, exchange_id:ExchangeID) -> Position:
    """
    Check if there is an open position to close
    Ex. If order_request is a close limit order for BTCUSDT with side='Buy',
    check if key positions:BTCUSDT:Sell exists
    """
    open_position_side = opposite_side(order_request.side)
    key = f"{exchange_id.value}:position:{order_request.symbol}:{open_position_side}"

    position_to_close = await redis.get(key)
    if position_to_close is None:
        raise InvalidOrderTypeException("No position to close")
    
    return Position(**json.loads(position_to_close))