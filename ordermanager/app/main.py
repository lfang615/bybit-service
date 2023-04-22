from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.websockets import WebSocketDisconnect
from fastapi.responses import HTMLResponse
from bson.json_util import dumps
from ordermanager.app.bybit import BybitAPI, BybitAPIException
from ordermanager.app.models.request.order import OrderRequest, CancelRequest, LeverageRequest
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from asyncio import Queue
from typing import Optional
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import redis.asyncio as redis
from typing import List
import asyncio
import json
import logging
import uuid
from typing import List


app = FastAPI()

# Configure the static files middleware to serve files from the `/static` folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'static')

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
# ---------------------------------------------------------------------------

orders_websockets = []
positions_websockets = []

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

@app.get("/", response_class=HTMLResponse)
async def serve_vue_app(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logging.error("Error serve_vue_app, {e}")
        return HTMLResponse(status_code=404)

@app.get("/order/")
async def get_order(order_id: Optional[str]=None, symbol: Optional[str]=None):
    try:
        if order_id:
            response = await api.ContractOrder(api).get_order_by_id(order_id)
        elif symbol:
            response = await api.ContractOrder(api).get_order_by_symbol(symbol)
        else:
            return {"error": "You must provide either an orderId or a symbol"}
        return response
    except (BybitAPIException, Exception) as e:
        logging.error("Error get_order, {e}")
        return {"error": str(e)}

@app.get("/orders")
async def get_orders():
    try:
        orders_data = await app.state.redis_client.get("orders")
        if orders_data:
            orders = json.loads(orders_data)
            filtered_orders = [order for order in orders if order["orderStatus"] not in ["Cancelled", "Deactivated"]]
            return filtered_orders
        else:
            return []
    except Exception as e:
        logging.error("Error get_orders, {e}")
        return {"error": str(e)}

@app.get("/positions")
async def get_positions():
    try:
        positions_data = await app.state.redis_client.get("positions")
        if positions_data:
            positions = json.loads(positions_data)
            filtered_positions = [
                position for position in positions
                if position["Buy"]["qty"] != 0 or position["Sell"]["qty"] != 0
            ]
            return filtered_positions
        else:
            return []
    except Exception as e:
        logging.error("Error get_positions, {e}")
        return {"error": str(e)}

@app.post("/place_order")
async def place_order(orderRequest: OrderRequest):
    try:
        orderRequest['orderLinkId'] = generate_unique_id()
        
        response = await api.ContractOrder(api).place_order(orderRequest)
        
        # Create a new order object in "Orders" cache
        order_data = orderRequest.dict()
        orderRequest['orderStatus'] = "Pending"   
        app.state.redis_client.hset("orders", orderRequest['orderLinkId'], json.dumps(order_data))

        if response['retCode'] == 0:
            await produce_topic_orders_executed(app, response['result'])
        # Publish order ID to order_updates channel
        # app.state.redis_client.publish("order_updates", order_placed['result']['orderId'])
        return response
    except (BybitAPIException, Exception) as e:
        logging.error("Error place_order, {e}")
        return {"error": str(e)}
    
@app.post("/cancel_order/{order_id}")
async def cancel_order(order_id: str):
    try:
        return await api.ContractOrder(api).cancel_order(order_id)
    except (BybitAPIException, Exception) as e:
        logging.error("Error cancel_order, {e}")
        return {"error": str(e)}

@app.post("/set_leverage")
async def set_leverage(leverageRequest: LeverageRequest):
    try:
        response = await api.Position(api).set_leverage(leverageRequest)
        return response
    except (BybitAPIException, Exception) as e:
        logging.error("Error set_leverage, {e}")
        return {"error": str(e)}

# ----------------------------- WEBSOCKET Connections for frontend updates  ---------------------------------
@app.websocket("/ws/orders")
async def orders_websocket(websocket: WebSocket):
    await websocket.accept()
    orders_websockets.append(websocket)
    try:
        while True:
            message = await websocket.receive_json()
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/positions")
async def positions_websocket(websocket: WebSocket):
    await websocket.accept()
    positions_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_json()  # Keep the connection alive
    except WebSocketDisconnect:
        positions_websockets.remove(websocket)

async def send_orders_update(order):
    try:
        for websocket in orders_websockets:
            await websocket.send_json(order)
    except Exception as e:
        logging.error(f"Error ws orders update: {e}")

async def send_positions_update(position):
    try:
        for websocket in positions_websockets:
            await websocket.send_json(position)
    except Exception as e:
        logging.error(f"Error ws positions update: {e}")

# --------------------------- BACKGROUND TASKS -------------------------------

async def produce_topic_orders_executed(app, order):
    try:
        producer = app.state.kafka_producer
        message = json.dumps(order)

        logging.warning(f"Sending message: {message}")
        # Publish the message to the Kafka topic
        await producer.send("orders_executed", message.encode("utf-8"))
    except Exception as e:
        logging.error(f"Error produce_topic_orders_executed: {e}")


async def consume_topic_orders_resolved(consumer):
    try:
        while True:
            logging.warning("Starting: consume_topic_orders_resolved")
            
            messages = await consumer.getmany(timeout_ms=1000)

            for tp, batch in messages.items():
                for message in batch:
                    order = message.value
                    resolved_order = json.dumps(order)
                    logging.warning(f"Received order from topic resolved_orders: {resolved_order}")

                    # Send the updated order to the WebSocket queue to update the UI
                    await send_orders_update(resolved_order)
    except Exception as e:
        logging.error(f"Error consume_topic_orders_resolved: {e}")
    finally:
        await consumer.stop()


async def consume_topic_positions_updated(consumer):
    try:
        while True:
            logging.warning("Starting: consume_positions_updated")
            
            messages = await consumer.getmany(timeout_ms=1000)

            for tp, batch in messages.items():
                for message in batch:
                    order = message.value
                    updated_position = json.dumps(order)
                    logging.warning(f"Received order from topic resolved_orders: {updated_position}")

                    # Send the updated order to the WebSocket queue to update the UI
                    await send_positions_update(updated_position)
    except Exception as e:
        logging.error(f"Error consume_topic_positions_updated: {e}")
    finally:
        await consumer.stop()  


# -------- STARTUP EVENTS ------------

class AppState:
    def __init__(self):
        self.kafka_producer = None
        self.redis_client = None
        self.kafka_consumer_orders = None
        self.kafka_consumer_positions = None
        self.kafka_consume_orders_task = None
        self.kafka_consume_positions_task = None

@app.on_event("startup")
async def startup_event():
    try:
        logging.warning("Application startup event")
        app.state = AppState()
        app.state.redis_client = redis.Redis(host=os.environ['REDIS_HOST'], port=os.environ['REDIS_PORT'], db=0)

        # Create Kafka producer
        app.state.kafka_producer = AIOKafkaProducer(bootstrap_servers=os.environ['KAFKA_URI'])
        await app.state.kafka_producer.start()

        app.state.kafka_consumer_orders = AIOKafkaConsumer(
            "orders_resolved",
            bootstrap_servers=os.environ['KAFKA_URI'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await app.state.kafka_consumer_orders.start()

        app.state.kafka_consumer_positions = AIOKafkaConsumer( 
            "positions_updated",
            bootstrap_servers=os.environ['KAFKA_URI'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await app.state.kafka_consumer_positions.start()
        
        app.state.kafka_consume_orders_task = asyncio.create_task(consume_topic_orders_resolved(app.state.kafka_consumer_orders))
        app.state.kafka_consume_positions_task = asyncio.create_task(consume_topic_positions_updated(app.state.kafka_consumer_positions))
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
    if app.state.kafka_consume_orders_task is not None:
        app.state.kafka_consume_orders_task.cancel()
        try:
            await app.state.kafka_consume_orders_task
        except asyncio.CancelledError:
            pass

    if app.state.kafka_consume_positions_task is not None:
        app.state.kafka_consume_positions_task.cancel()
        try:
            await app.state.kafka_consume_positions_task
        except asyncio.CancelledError:
            pass

    # Stop the Kafka consumers
    if app.state.kafka_consumer_orders is not None:
        await app.state.kafka_consumer_orders.stop()

    if app.state.kafka_consumer_positions is not None:
        await app.state.kafka_consumer_positions.stop()