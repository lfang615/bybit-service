import os
import json
import asyncio
from fastapi import FastAPI
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import httpx
import aioredis
from dotenv import load_dotenv
from pydantic import BaseModel

app = FastAPI()
redis_client = None
kafka_producer = None

class OrderRequest(BaseModel):
    orderLinkId: str
    orderStatus: str
    symbol: str
    side: str
    qty: int
    reduceOnly: bool

load_dotenv()
BYBIT_API_KEY = os.environ.get("BYBIT_API_KEY")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET")
BYBIT_BASE_URL = "https://api.bybit.com"

async def execute_order(order: OrderRequest):
    headers = {
        "api-key": BYBIT_API_KEY,
        "api-secret": BYBIT_API_SECRET,
    }

    payload = {
        "orderLinkId": order.orderLinkId,
        "symbol": order.symbol,
        "side": order.side,
        "qty": order.qty,
        "reduceOnly": order.reduceOnly
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BYBIT_BASE_URL}/v2/private/order/create", headers=headers, params=payload)

    return response.json()

async def update_positions_cache(redis_client, order: OrderRequest):
    positions_key = f"positions:{order.symbol}"
    position_data = await redis_client.get(positions_key)

    if position_data:
        position_data = json.loads(position_data)
    else:
        position_data = {
            "Buy": {"qty": 0},
            "Sell": {"qty": 0}
        }

    if order.side == "Buy":
        position_data["Buy"]["qty"] += order.qty
    elif order.side == "Sell":
        position_data["Sell"]["qty"] += order.qty

    await redis_client.set(positions_key, json.dumps(position_data))

async def process_order(order: OrderRequest):
    bybit_order = await execute_order(order)
    order_status = bybit_order['orderStatus']
    
    if order_status in ["Filled", "PartiallyFilled"]:
        await update_positions_cache(redis_client, order)
        await kafka_producer.send("resolved_orders", key=order.orderLinkId.encode(), value=json.dumps(order.dict()).encode())

async def consume_orders_executed():
    kafka_consumer = AIOKafkaConsumer("orders_executed", bootstrap_servers=os.environ['KAFKA_URI'], value_deserializer=lambda m: json.loads(m.decode("utf-8")))
    await kafka_consumer.start()

    try:
        async for msg in kafka_consumer:
            order = OrderRequest(**msg.value)
            await process_order(order)
    finally:
        await kafka_consumer.stop()

@app.on_event("startup")
async def startup_event():
    global redis_client
    global kafka_producer

    # Initialize Redis client
    redis_client = aioredis.from_url("redis://localhost:6379")

    # Initialize Kafka producer
    kafka_producer = AIOKafkaProducer(bootstrap_servers=os.environ['KAFKA_URI'])

        
# async def bg_task_fetch_trading_symbols(interval: int):
#     while True:
#         response = api.MarketData(api).get_trading_symbols()
#         if response['retMsg'] == 'OK':
#             symbols = response['result']['list']
#             for symbol in symbols:
#                 # Use the symbol name as the key, and store the symbol data as a JSON string
#                 app.state.redis_client.set(symbol['symbol'], symbol['symbol'])
#             await asyncio.sleep(interval)  # Sleep for the specified interval (in seconds) before fetching again

# @app.on_event("startup")
# async def startup_event():
#     # Start the background task
#     asyncio.create_task(bg_task_fetch_trading_symbols(60))