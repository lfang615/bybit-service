from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect
from bson.json_util import dumps
from backend.app.bybit import BybitAPI
from backend.app.models.request.order import OrderRequest, CancelRequest, LeverageRequest
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from pymongo import MongoClient
from asyncio import Queue
from typing import Optional
import os
from dotenv import load_dotenv
import redis
import asyncio
import json
import logging


app = FastAPI()
app.websocket_queue = Queue()

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
redis_client = redis.Redis(host=os.environ['REDIS_HOST'], port=os.environ['REDIS_PORT'], db=0)
api = BybitAPI(api_key=os.environ['BYBIT_API_KEY'], secret_key=os.environ['BYBIT_API_SECRET'])

#------------------------- REST API ---------------------------------
@app.get("/symbols")
async def get_symbols():
    all_keys = redis_client.keys('*')
    decoded_keys = [key.decode('utf-8') for key in all_keys]
    return decoded_keys

@app.get("/position")
async def get_position():
    return await api.Position(api).get_all_positions()

@app.get("/open_positions_orders")
async def get_open_positions_orders():
    filter_conditions = {
        "$or": [
            {"isPositionClosed": False},
            {"isReduceOnly": True, "orderStatus": {"$ne": "Filled"}},
        ],
    }
    orders = list(app.state.order_collection.find(filter_conditions))
    orders_json = json.loads(dumps(orders))
    return orders_json

@app.get("/order/")
async def get_order(order_id: Optional[str]=None, symbol: Optional[str]=None):
    if order_id:
        response = await api.ContractOrder(api).get_order_by_id(order_id)
    elif symbol:
        response = await api.ContractOrder(api).get_order_by_symbol(symbol)
    else:
        return {"error": "You must provide either an order_id or a symbol"}
    return response
    # order_data = response['result']['list'][0]
    # order_data['isPositionClosed'] = False
    # app.state.order_collection.insert_one(order_data)
    
    

@app.get("/mongo")
async def get_open_orders_mongo():
    order = app.state.order_collection.find({})
    return order

@app.post("/place_order")
async def place_order(orderRequest: OrderRequest):
    response = await api.ContractOrder(api).place_order(orderRequest)

    print(response['result']['orderId'])
    order_data = orderRequest.dict()
    
    # Assign the order ID to the order data
    order_data['orderId'] = response['result']['orderId']
    # Assign orderStatus as New
    order_data['orderStatus'] = "New"
    order_data['isPositionClosed'] = False
    app.state.order_collection.insert_one(order_data)

    # Produce a message with the order to the kafka topic
    await produce_order_status_updates(app, response['result'])
    # Publish order ID to order_updates channel
    # redis_client.publish("order_updates", order_placed['result']['orderId'])

    return response

@app.get("/position_status/{symbol}")
async def get_position_status(symbol: str):
    return await api.Position(api).get_position_status(symbol)

# @app.post("/cancel_order/{order_id}")
# async def cancel_order(order_id: str):
#     return await api.ContractOrder(api).cancel_order(order_id)

@app.post("/set_leverage")
async def set_leverage(leverageRequest: LeverageRequest):
    response = await api.Position(api).set_leverage(leverageRequest)
    return response

@app.get("/openOrders")
async def get_open_orders():
    return await api.ContractOrder(api).get_open_orders()

async def produce_order_status_updates(app, order):
    producer = app.state.kafka_producer

    # Serialize the order object as JSON
    message = json.dumps(order)
    logging.warning(f"Sending message: {message}")
    # Publish the message to the Kafka topic
    await producer.send("order_status_updates", message.encode("utf-8"))


# ----------------------------- WEBSOCKET ---------------------------------
@app.websocket("/ws/order_updates")
async def websocket_order_updates(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await app.websocket_queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass

    
# --------------------------- BACKGROUND TASKS -------------------------------

async def bg_task_fetch_trading_symbols(interval: int):
    while True:
        response = api.MarketData(api).get_trading_symbols()
        if response['retMsg'] == 'OK':
            symbols = response['result']['list']
            for symbol in symbols:
                # Use the symbol name as the key, and store the symbol data as a JSON string
                redis_client.set(symbol['symbol'], symbol['symbol'])
            await asyncio.sleep(interval)  # Sleep for the specified interval (in seconds) before fetching again


async def order_status_checker(producer):
    logging.warning("order_status_checker started")
    while True:
        orders = list(app.state.order_collection.find({"orderStatus": {"$ne": "Cancelled"}, "isPositionClosed": False}))
        for order in orders:
            order_id = order["orderId"]
            response = await api.ContractOrder(api).get_order_by_id(order_id)
            bybit_order = response['result']['list'][0]

            order_status = bybit_order['orderStatus']
            cum_exec_qty = bybit_order["cumExecQty"]

            should_update = False

            if order_status == "PartiallyFilled" and order["cumExecQty"] != cum_exec_qty:
                should_update = True
            elif order_status != order["orderStatus"]:
                should_update = True

            if should_update:
                logging.warning(f"logging bybit_order: {json.dumps(bybit_order)}")
                await producer.send(
                    "order_status_updates",
                    key=order_id.encode(),
                    value=json.dumps(bybit_order).encode(),
                )
                logging.warning(f"Order sent to Kafka: {json.dumps(bybit_order)}")
            await producer.flush()
        await asyncio.sleep(5)


async def consume_order_status_updates(app, consumer):
    try:
        while True:
            logging.warning("Checking for messages in Kafka consumer")
            # Consume messages using the getmany() method
            messages = await consumer.getmany(timeout_ms=1000)

            for tp, batch in messages.items():
                for message in batch:
                    order = message.value
                    filled_order = json.dumps(order)
                    logging.warning(f"Received order from Kafka: {filled_order}")

                    # Update the order in the database
                    filter = {'orderId': order['orderId']}
                    update = {'$set': order}
                    app.state.order_collection.update_many(filter, update)

                    # Send the updated order to the WebSocket queue to update the UI
                    await app.websocket_queue.put(order)  # 
                    
    finally:
        # Make sure to stop the consumer when you're done
        await consumer.stop()  



# -------- STARTUP EVENTS ------------

class AppState:
    def __init__(self):
        self.mongodb_client = None
        self.kafka_producer = None
        self.redis_client = None
        self.websocket_queue = asyncio.Queue()

@app.on_event("startup")
async def startup_event():
    logging.warning("Application startup event")
    app.state = AppState()

    app.state.kafka_consumer = AIOKafkaConsumer(
        "order_status_updates",
        bootstrap_servers="localhost:9092",
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    await app.state.kafka_consumer.start()
    app.state.kafka_consumer_task = asyncio.create_task(consume_order_status_updates(app, app.state.kafka_consumer))

    app.state.kafka_producer = AIOKafkaProducer(bootstrap_servers='localhost:9092')
    await app.state.kafka_producer.start()
    app.state.kafka_producer_task = asyncio.create_task(order_status_checker(app.state.kafka_producer))

    app.state.mongodb_client = MongoClient("mongodb://localhost:27017")
    app.state.mongodb = app.state.mongodb_client.order_db
    app.state.order_collection = app.state.mongodb.orders
    # Start the background task when the application starts, fetching trading symbols every 24 hours
    # asyncio.create_task(bg_task_fetch_trading_symbols(interval=86400))
    

@app.on_event("shutdown")
async def shutdown_event():
    logging.warning("Application shutdown event")
     # Stop the Kafka producer
    if app.state.kafka_producer is not None:
        await app.state.kafka_producer.stop()

    # Cancel the Kafka consumer task
    if app.state.kafka_consumer_task is not None:
        app.state.kafka_consumer_task.cancel()
        try:
            await app.state.kafka_consumer_task
        except asyncio.CancelledError:
            pass

    # Close the MongoDB client
    if app.state.mongodb_client is not None:
        app.state.mongodb_client.close()