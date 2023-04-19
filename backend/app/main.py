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
import redis.asyncio as redis
import asyncio
import json
import logging
import uuid

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
api = BybitAPI(api_key=os.environ['BYBIT_API_KEY'], secret_key=os.environ['BYBIT_API_SECRET'])

def generate_unique_id():
    return str(uuid.uuid4())

#------------------------- REST API ---------------------------------
@app.get("/symbols")
async def get_symbols():
    all_keys = app.state.redis_client.keys('*')
    decoded_keys = [key.decode('utf-8') for key in all_keys]
    return decoded_keys


@app.get("/position")
async def get_position():
    return await api.Position(api).get_all_positions()


@app.get("/order/")
async def get_order(order_id: Optional[str]=None, symbol: Optional[str]=None):
    if order_id:
        response = await api.ContractOrder(api).get_order_by_id(order_id)
    elif symbol:
        response = await api.ContractOrder(api).get_order_by_symbol(symbol)
    else:
        return {"error": "You must provide either an orderId or a symbol"}
    return response
    

@app.post("/place_order")
async def place_order(orderRequest: OrderRequest):

    orderRequest['orderLinkId'] = generate_unique_id()
    
    response = await api.ContractOrder(api).place_order(orderRequest)

    # Create a new order object in "Orders" cache
    order_data = orderRequest.dict()
    orderRequest['orderStatus'] = "Pending"   
    app.state.redis_client.hset("orders", orderRequest['orderLinkId'], json.dumps(order_data))

    # Produce a message with the new order to the kafka topic
    await produce_topic_orders_executed(app, response['result'])
    # Publish order ID to order_updates channel
    # app.state.redis_client.publish("order_updates", order_placed['result']['orderId'])

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

async def produce_topic_orders_executed(app, order):
    producer = app.state.kafka_producer
    message = json.dumps(order)

    logging.warning(f"Sending message: {message}")
    # Publish the message to the Kafka topic
    await producer.send("orders_executed", message.encode("utf-8"))


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

async def consume_topic_resolved_orders(app, consumer):
    try:
        while True:
            logging.warning("Starting: consume_topic_resolved_orders")
            
            messages = await consumer.getmany(timeout_ms=1000)

            for tp, batch in messages.items():
                for message in batch:
                    order = message.value
                    filled_order = json.dumps(order)
                    logging.warning(f"Received order from topic resolved_orders: {filled_order}")

                    # Send the updated order to the WebSocket queue to update the UI
                    await app.websocket_queue.put(order)
    finally:
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
    app.state.redis_client = redis.Redis(host=os.environ['REDIS_HOST'], port=os.environ['REDIS_PORT'], db=0)
    app.state.kafka_consumer = AIOKafkaConsumer(
        "order_status_updates",
        bootstrap_servers=os.environ['KAFKA_URI'],
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    await app.state.kafka_consumer.start()
    app.state.kafka_consumer_task = asyncio.create_task(consume_topic_resolved_orders(app, app.state.kafka_consumer))

    app.state.kafka_producer = AIOKafkaProducer(bootstrap_servers=os.environ['KAFKA_URI'])
    await app.state.kafka_producer.start()

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