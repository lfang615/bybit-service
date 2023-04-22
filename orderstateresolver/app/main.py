import os
import json
import asyncio
from fastapi import FastAPI
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import httpx
import redis.asyncio as redis
from dotenv import load_dotenv
from pydantic import BaseModel
import logging
from orderstateresolver.app.bybit import BybitAPI
import datetime



app = FastAPI()
load_dotenv()
bybit_client = BybitAPI(os.environ['BYBIT_API_KEY'], os.environ['BYBIT_API_SECRET'])

async def update_positions_cache(redis_client, bybit_order, reduce_only=False):
    logging.log(logging.INFO, f"Begin Updating positions cache for {bybit_order.symbol}")
    
    positions_key = f"positions:{bybit_order.symbol}"
    position_data = await redis_client.get(positions_key)

    if position_data:
        position_data = json.loads(position_data)
    else:
        position_data = {
            "Buy": {
                "openDate": datetime.today().strftime("%m/%d/%Y %H:%M"),
                "qty": 0,
                "aep": bybit_order["price"],
                "linkedOrders": [bybit_order],
                "contractData": bybit_order
            },
            "Sell": {"qty": 0, "contractData": bybit_order}
        }

    # Update position qty
    if bybit_order.side == "Buy":
        logging.log(logging.INFO, f"Updating Buy position for {bybit_order.symbol}")
        if reduce_only:
            position_data["Buy"]["qty"] -= bybit_order.qty         
            if position_data["Buy"]["qty"] == 0:
                clear_linked_orders("Buy", position_data)
        else:
            position_data["Buy"]["qty"] += bybit_order.qty

    if bybit_order.side == "Sell":
        logging.log(logging.INFO, f"Updating Sell position for {bybit_order.symbol}")
        if reduce_only:
            position_data["Sell"]["qty"] -= bybit_order.qty
            if position_data["Sell"]["qty"] == 0:
                clear_linked_orders("Sell", position_data)  
        else:
            position_data["Sell"]["qty"] += bybit_order.qty

    await redis_client.set(positions_key, json.dumps(position_data))
    logging.log(logging.INFO, f"End Updating positions cache for {bybit_order.symbol}")  
    await send_position_updated_message(position_data)


def clear_linked_orders(side, position_data):
    position_data[side]["linkedOrders"] = []
    position_data[side]["aep"] = 0

async def calculate_aep(position_data, bybit_order, side):
    # AEP (Average Entry Price) = (Sum of price of each linked order) / (Number of linked orders)
    # If orderLinkId is already in the list of linked orders, status changed from "PartiallyFilled" to "Filled" so use the same aep
    if side == "Buy":
        if bybit_order["orderLinkId"] not in position_data["Buy"]["linkedOrders"]:
            position_data["Buy"]["linkedOrders"].append(bybit_order["orderLinkId"])
            position_data["Buy"]["aep"] = (position_data["Buy"]["aep"] + bybit_order.price) / len(position_data["Buy"]["linkedOrders"])
        
    if side == "Sell":
        if bybit_order["orderLinkId"] not in position_data["Sell"]["orderLinkIds"]:
            position_data["Sell"]["orderLinkIds"].append(bybit_order["orderLinkId"])
            position_data["Sell"]["aep"] =  (position_data["Sell"]["aep"] + bybit_order.price) / len(position_data["Sell"]["orderLinkIds"])


async def format_short_position(position_data):
    return {
        "symbol": position_data["contractData"]["symbol"],
        "side": position_data["contractData"]["side"],
        "qty": position_data["qty"],
        "contractData": position_data["contractData"]
    }

async def process_order_updates(order):
    logging.warning("check_order_status started")
    order_link_id = order["orderLinkId"]

    while True:
        # Call Bybit API to get order information
        order_info = await bybit_client.get_order_by_orderLinkId(order_link_id)
        
        if order_info["orderStatus"] in ["Filled", "PartiallyFilled"] and order_info['reduceOnly'] is False:
            await update_positions_cache(app.state.redis_client, order_info, reduce_only=False)
        elif order_info["orderStatus"] in ["Filled", "PartiallyFilled"] and order_info['reduceOnly'] is True:
            await update_positions_cache(app.state.redis_client, order_info, reduce_only=True)
        elif order_info["orderStatus"] in ["Cancelled", "Deactivated"]:
            # Update the cache with the new order status
            await app.state.redis_client.set(f"orders:{order['orderLinkId']}", json.dumps(order_info))
            # Send a 'order_resolved' message containing the order
            await send_order_resolved_message(order_info)
            # Exit the loop
            break
        
    # Wait for some time before checking the order status again
    await asyncio.sleep(5)  


async def send_order_resolved_message(order):
    try:
        await app.state.kafka_producer.send("orders_resolved", key=order.orderLinkId.encode(), value=json.dumps(order).encode())
        logging.log(logging.WARNING, f"Sent order resolved message: {order}")
    except Exception as e:
        logging.log(logging.ERROR, f"Error sending order resolved message: {e}")

async def send_position_updated_message(order):
    try:
        await app.state.kafka_producer.send("position_updated", key=order.orderLinkId.encode(), value=json.dumps(order).encode())
        logging.log(logging.WARNING, f"Sent position updated message: {order}")
    except Exception as e:
        logging.log(logging.ERROR, f"Error sending position updated message: {e}")

async def consume_orders_executed(consumer):
    try:
        async for msg in consumer:
            order = msg.value
            logging.log(logging.WARNING, f"Received order: {order}")
            await app.state.redis_client.set(f"orders:{order.orderLinkId}", json.dumps(order))
            await process_order_updates(order)
    finally:
        await consumer.stop()


async def update_symbols_cache(redis_client):
    logging.log(logging.WARNING, f"Begin Updating symbols cache")
    response = await bybit_client.get_trading_symbols()
    if response.status_code == 200:
        symbols = response.json()["data"]
        symbol_list = [symbol["symbol"] for symbol in symbols]

        await redis_client.set("symbols", json.dumps(symbol_list))
        logging.log(logging.WARNING, f"Symbols cache updated")
        return True
    else:
        return False


async def symbols_updater_task():
    while True:
        update_successful = await update_symbols_cache(app.state.redis_client)
        if update_successful:
            await asyncio.sleep(24 * 60 * 60)  # Sleep for 24 hours
        else:
            await asyncio.sleep(60)  # Sleep for a minute before retrying

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