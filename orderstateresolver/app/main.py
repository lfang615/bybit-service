import os
import json
import asyncio
from fastapi import FastAPI
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import redis.asyncio as redis
from dotenv import load_dotenv
import logging
from orderstateresolver.app.bybit import BybitAPI
import datetime
from orderstateresolver.app.models.position import Position
from orderstateresolver.app.models.order import Order, OrderStatus, OrderSide
from orderstateresolver.app.retrysettings import bybit_circuit_breaker, kafka_circuit_breaker, redis_circuit_breaker, retry_decorator


app = FastAPI()
load_dotenv()

# ----------------- Bybit API Client Wrapper -----------------
bybit_client = BybitAPI(os.environ['BYBIT_API_KEY'], os.environ['BYBIT_API_SECRET'])

@retry_decorator
@bybit_circuit_breaker
async def bybit_api_wrapper(api_function, *args, **kwargs):
    return await api_function(*args, **kwargs)


async def update_positions_cache(bybit_order:Order):
    positions_key = get_position_cache_key(bybit_order)
    logging.log(logging.INFO, f"Begin Updating positions cache for {positions_key}")
    position_data = await get_cache_value(positions_key)

    if position_data:
        position = Position(**json.loads(position_data))
    else:
        position = Position(symbol=bybit_order.symbol,
                             side=bybit_order.side, 
                             openDate=datetime.datetime.now().strftime("%m/%d/%Y %H:%M"), 
                             qty=0, 
                             aep=bybit_order.price,
                             linkedOrders=[])

    logging.log(logging.INFO, f"Updating {bybit_order.side} position for {bybit_order.symbol}")
    
    calculate_position_totals(position, bybit_order)

    # If the position is closed (Filled order qty of reduceOnly=True orders LESS qty of Filled reduceOnly=False orders)
    # then set the close date and delete the position from cache        
    if position.qty == 0:
        position.closeDate = datetime.datetime.now().strftime("%m/%d/%Y %H:%M")
        logging.log(logging.INFO, f"Closing position {positions_key} Date:{position.closeDate}")
        await delete_cache_value(f"positions:{position.symbol}:{position.side}")
        logging.log(logging.INFO, f"Deleted position {positions_key} from cache")
        return position
    
    await set_cache_value(positions_key, position)
    logging.log(logging.INFO, f"End Updating positions cache for {positions_key}")  
    return position


def get_position_cache_key(bybit_order:Order):
    if bybit_order.reduceOnly and bybit_order.side == OrderSide.SELL.value:
        return f"positions:{bybit_order.symbol}:{OrderSide.BUY.value}"
    elif bybit_order.reduceOnly and bybit_order.side == OrderSide.BUY.value:
        return f"positions:{bybit_order.symbol}:{OrderSide.SELL.value}"
    else:
        return f"positions:{bybit_order.symbol}:{bybit_order.side}"


def calculate_position_totals(position:Position, bybit_order:Order):
    # AEP (Average Entry Price) = (Sum of price of each linked order) / (Number of linked orders)
    # Qty = (Sum of cumExecQty of each linked order)
    # If orderLinkId is already in the list of linked orders, replace the order with the updated order and calculate
    
    if position.linkedOrders == []:
        # No linked orders means this is the first order for this position. Add the order to the linked orders list 
        # Initial AEP and Qty of position is set to the order's price and cumExecQty
        position.linkedOrders.append(bybit_order)
        position.aep = bybit_order.price
        position.qty = bybit_order.cumExecQty
        return
    
    if bybit_order.orderLinkId not in [o.orderLinkId for o in position.linkedOrders]:
        position.linkedOrders.append(bybit_order)
        position.aep = sum(p.price for p in position.linkedOrders if p.reduceOnly is False) / float(sum(1 for p in position.linkedOrders if p.reduceOnly is False))
        position.qty = calculate_position_qty(position)
    elif bybit_order.orderLinkId in [o.orderLinkId for o in position.linkedOrders]:
        for idx, order in enumerate(position.linkedOrders):
            if order.orderLinkId == bybit_order.orderLinkId:
                position.linkedOrders[idx] = bybit_order
                position.qty = calculate_position_qty(position)


def calculate_position_qty(position:Position):
    p_increasing_qty = sum(o.cumExecQty for o in position.linkedOrders if o.reduceOnly is False)
    p_deacreasing_qty = sum(o.cumExecQty for o in position.linkedOrders if o.reduceOnly is True)
    return p_increasing_qty - p_deacreasing_qty


async def process_order_updates(order:Order):
    logging.warning("check_order_status started")
    order_link_id = order["orderLinkId"]

    while True:
        # Call Bybit API to get order information
        bybit_response = await bybit_client.get_order_by_orderLinkId(order_link_id)
        bybit_order = Order(**bybit_response["result"]["list"][0])

        cached_order = app.state.get_cache_value(f"orders:{order_link_id}")
        order = Order(**json.loads(cached_order))

        if bybit_order["orderStatus"] in [OrderStatus.FILLED.value, OrderStatus.PARTIALLY_FILLED.value]:
            # For Filled or PartiallyFilled orders, update the positions cache with filled order values
            position = await update_positions_cache(bybit_order)
            await send_position_updated_message(position)
            logging.warning("Sent position updated message for {position.symbol}")

        if bybit_order["orderStatus"] in [OrderStatus.FILLED.value, OrderStatus.CANCELLED.value, OrderStatus.TRIGGERED.value, OrderStatus.DEACTIVATED.value, OrderStatus.REJECTED.value]:
            # Update the cache with the new order status
            await set_cache_value(f"orders:{order['orderLinkId']}", bybit_order)
            # Send a 'order_resolved' message containing the order
            await send_order_resolved_message(order)
            logging.warning("Sent order resolved message for {order.orderLinkId}")
            # Exit the loop
            break
        if bybit_order["orderStatus"] not in [OrderStatus.FILLED.value, OrderStatus.PARTIALLY_FILLED.value, OrderStatus.CANCELLED.value, OrderStatus.TRIGGERED.value, OrderStatus.DEACTIVATED.value, OrderStatus.REJECTED.value]:
            # Log unforseen scenarios just in case
            logging.exception(f"process_order_updates, unforseen scenario for {json.dumps(bybit_order)}")
            break
        
    # Wait for some time before checking the order status again
    await asyncio.sleep(5)
  

# ------------------------ Kafa Producers ------------------------
@retry_decorator
@kafka_circuit_breaker
async def send_order_resolved_message(order:Order):
    try:
        await app.state.kafka_producer.send("orders_resolved", key=order.orderLinkId.encode(), value=json.dumps(order).encode())
        logging.log(logging.WARNING, f"Sent order resolved message: {order.orderLinkId}")
    except Exception as e:
        logging.log(logging.ERROR, f"Error sending order resolved message: {order.orderLinkId} : {e}")

@retry_decorator
@kafka_circuit_breaker
async def send_position_updated_message(position:Position):
    try:
        message_key = f"{position.symbol}:{position.side}".encode()
        await app.state.kafka_producer.send("position_updated", key=message_key, value=json.dumps(position).encode())
        logging.log(logging.WARNING, f"Sent position updated message: {position.symbol}:{position.side}")
    except Exception as e:
        logging.log(logging.ERROR, f"Error sending position {position.symbol}:{position.side} updated message: {e}")

@retry_decorator
@kafka_circuit_breaker
async def send_position_closed_message(position:Position):
    try:
        message_key = f"{position.symbol}:{position.side}".encode()
        await app.state.kafka_producer.send("position_closed", key=message_key, value=json.dumps(position).encode())
        logging.log(logging.WARNING, f"Sent position closed message: {position.symbol}:{position.side}")
    except Exception as e:
        logging.log(logging.ERROR, f"Error sending position {position.symbol}:{position.side} closed message: {e}")
    pass
# ---------------------------------------------------------------------------------

# ------------------------ Kafa Consumers -----------------------------------------
async def consume_orders_executed(consumer):
    try:
        async for msg in consumer:
            order = msg.value
            logging.log(logging.WARNING, f"Received order: {order}")
            set_cache_value(f"orders:{order.orderLinkId}", order)
            await process_order_updates(Order(**order))
            
    finally:
        await consumer.stop()



# ------------------Background task to update the symbols cache ------------------
async def update_symbols_cache():
    try:
        logging.log(logging.WARNING, f"Begin Updating symbols cache")
        response = await bybit_client.get_trading_symbols()
        if response['retCode'] == 0:
            symbols = response['result']["list"]
            symbol_list = [symbol["symbol"] for symbol in symbols]

            await set_cache_value("symbols", symbol_list)
            logging.log(logging.WARNING, f"Symbols cache updated")
            return True
        else:
            logging.log(logging.ERROR, f"Error updating symbols cache: {response}")
            return False
    except Exception as e:
        logging.log(logging.ERROR, f"Error updating symbols cache: {e}")
        return False

async def symbols_updater_task():
    while True:
        update_successful = await update_symbols_cache()
        if update_successful:
            await asyncio.sleep(24 * 60 * 60)  # Sleep for 24 hours
        else:
            await asyncio.sleep(60)  # Sleep for a minute before retrying
    
# ------------------Background task to update the risk limits cache ------------------
async def update_risk_limits_cache():
    try:
        logging.log(logging.WARNING, f"Begin Updating risk limits cache")
        response = await bybit_client.get_risk_limits()
        if response['retCode'] == 0:
            risk_limits = response["result"]["list"]

            # Personal risk limit settings
            lowest_risk_limits = [limit for limit in risk_limits if limit["isLowestRisk"] == 1]
            await set_cache_value("risk_limits", lowest_risk_limits)
            logging.log(logging.WARNING, f"Risk limits cache updated")
            return True
        else:
            return False
    except Exception as e:
        logging.log(logging.ERROR, f"Error updating risk limits cache: {e}")
        return False
    
async def risk_limits_updater_task():
    while True:
        update_successful = await update_risk_limits_cache()
        if update_successful:
            await asyncio.sleep(24 * 60 * 60)  # Sleep for 24 hours
        else:
            await asyncio.sleep(60)  # Sleep for a minute before retrying

# ---------------------------------------------------------------------------------------------
@retry_decorator
@redis_circuit_breaker
async def delete_cache_value(key: str):
    try:        
        await app.state.redis_client.delete(key)
    except Exception as e:
        logging.error(f"Error delete_cache_value, {e}")
        raise e

@retry_decorator
@redis_circuit_breaker
async def get_cache_value(key: str):
    try:        
        data = await app.state.redis_client.get(key)
        if data:
            return data
        else:
            return None
    except Exception as e:
        logging.error(f"Error get_from_redis_cache, {e}")
        raise e

@retry_decorator
@redis_circuit_breaker    
async def set_cache_value(key: str, data: dict):
    try:        
        await app.state.redis_client.set(key, json.dumps(data))
    except Exception as e:
        logging.error(f"Error set_cache_value, {e}")
        raise e

class AppState:
    def __init__(self):
        self.kafka_producer = None
        self.redis_client = None
        self.kafka_consumer = None
        self.consume_orders_executed_task = None
        self.symbols_update_task = None

@app.on_event("startup")
async def startup_event():
    try:
        logging.warning("Application startup event")
        app.state = AppState()
        app.state.redis_client = redis.Redis(host=os.environ['REDIS_HOST'], port=os.environ['REDIS_PORT'], db=0)
        app.state.kafka_producer = AIOKafkaProducer(bootstrap_servers=os.environ['KAFKA_URI'])
        await app.state.kafka_producer.start()
        
        app.state.kafka_consumer = AIOKafkaConsumer(
            "orders_executed", 
            bootstrap_servers=os.environ['KAFKA_URI'], value_deserializer=lambda m: json.loads(m.decode("utf-8")))
        
        await app.state.kafka_consumer.start()

        # Start consuming messages from the 'orders_executed' topic
        app.state.consume_orders_executed_task = asyncio.create_task(consume_orders_executed(app.state.kafka_consumer))

        # Start the symbols_updater_task
        app.state.symbols_update_task = asyncio.create_task(symbols_updater_task())
        app.state.risk_limits_update_task = asyncio.create_task(risk_limits_updater_task())
    except Exception as e:
        logging.error("Error during startup event, shutting down: %s", str(e))
        await shutdown_event()
        raise e
    

@app.on_event("shutdown")
async def shutdown_event():
    logging.warning("Application shutdown event")
    
     # Stop the Kafka producer
    if app.state.kafka_producer is not None:
        await app.state.kafka_producer.stop()

    # Cancel the Kafka consumer tasks
    if app.state.consume_orders_executed_task is not None:
        app.state.consume_orders_executed_task.cancel()
        try:
            await app.state.consume_orders_executed_task
        except asyncio.CancelledError:
            pass

    # Stop the Kafka consumers
    if app.state.kafka_consumer is not None:
        await app.state.kafka_consumer.stop()