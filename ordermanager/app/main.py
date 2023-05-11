from fastapi import FastAPI, WebSocket, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from starlette.websockets import WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException
from bson.json_util import dumps
from ordermanager.app.services.bybit import BybitAPI, ExchangeAPIException
from ordermanager.app.security import Security, User, Token
from ordermanager.app.models.order import *
from ordermanager.app.services.abstractexchange import CryptoExchangeAPI
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer, TopicPartition
import os
from dotenv import load_dotenv
import redis.asyncio as redis
from typing import Optional
import asyncio
import json
import logging
import uuid
from ordermanager.app.exceptions import ExchangeAPIException, InsufficientBalanceException, CachedDataException
from ordermanager.app.utils import *


app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
symbols = []
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
security = Security()

async def get_exchange_api(exchange_id: ExchangeID,
                           current_user: User = Depends(security.get_current_user)) -> CryptoExchangeAPI:

    api_key_key = f"{exchange_id.name.upper()}_API_KEY"
    secret_key_key = f"{exchange_id.name.upper()}_SECRET_KEY"

    api_key = os.getenv(api_key_key)
    secret_key = os.getenv(secret_key_key)

    if not api_key or not secret_key:
        raise HTTPException(status_code=400, detail=f"API keys not found for exchange {exchange_id.name}")

    return crypto_exchange_factory(api_key, secret_key, exchange_id)

def crypto_exchange_factory(api_key: str, secret_key: str, exchange_id: ExchangeID) -> CryptoExchangeAPI:
    if exchange_id == ExchangeID.BYBIT:
        return BybitAPI(api_key, secret_key)
    # Add more exchanges here as needed
    else:
        raise ValueError(f"Unsupported exchange ID: {exchange_id}")

def generate_unique_id():
    return str(uuid.uuid4())

def get_redis_client() -> redis.Redis:
    return app.state.redis

def crypto_exchange_factory(api_key: str, secret_key: str, exchange_id: ExchangeID) -> CryptoExchangeAPI:
    if exchange_id == ExchangeID.BYBIT:
        return BybitAPI(api_key, secret_key)
    # Add more exchanges here as needed
    else:
        raise ValueError(f"Unsupported exchange ID: {exchange_id}")


#------------------------- REST API ---------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_vue_app(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logging.error("Error serve_vue_app, {e}")
        return HTMLResponse(status_code=404)
        
@app.get("/symbols")
async def get_symbols(current_user: User = Depends(security.get_current_user), 
                      redis: redis.Redis = Depends(get_redis_client)):
    try:
        result = await get_cache_value("symbols", redis)
        symbol_list = json.loads(result)
        
        return JSONResponse(content=symbol_list, status_code=200)
    except (ExchangeAPIException, HTTPException, Exception) as e:
        logging.error("Error get_symbols, {e}")
        return {}
    
@app.get("/order/")
async def get_order(exchange_id: ExchangeID,
                    exchange_api: CryptoExchangeAPI = Depends(get_exchange_api),
                    current_user: User = Depends(security.get_current_user),
                    order_id: Optional[str]=None, symbol: Optional[str]=None):
    try:
        if order_id:
            response = await exchange_api.ContractOrder(exchange_api).get_order_by_id(order_id)
        elif symbol:
            response = await exchange_api.ContractOrder(exchange_api).get_order_by_symbol(symbol) 
        else:
            return {"error": "You must provide either an orderId or a symbol"}
        return response
    except (ExchangeAPIException, HTTPException) as e:
        logging.error("Error get_order, {e}")
        return JSONResponse(content={"error": str(e)}, status_code=400)


@app.get("/risk_limits/{symbol}")
async def get_risk_limits(symbol: str, redis: redis.Redis = Depends(get_redis_client)) -> JSONResponse:
    try:
        result = await get_cache_value(f"risk_limits:{symbol}", redis)
        risk_limits = json.loads(result)
        
        user_setting = await get_cache_value(f"Leverage:{symbol}", redis)
        if user_setting:
            response = LeverageResponse(**json.loads(user_setting))
            response.riskLimit = risk_limits
        else:
            response = LeverageResponse(symbol=symbol, maxLeverage=risk_limits["maxLeverage"])

        return JSONResponse(content=dict(response), status_code=200)
    except (ExchangeAPIException, HTTPException, Exception) as e:
        logging.error("Error get_risk_limits, {e}")
        return JSONResponse(content={"error": str(e)}, status_code=400)
    

@app.get("/orders")
async def get_orders(redis: redis.Redis = Depends(get_redis_client)) -> JSONResponse:
    try:
        orders_data = await get_cache_value("orders", redis)
        if orders_data:
            orders = json.loads(orders_data)
            filtered_orders = [order for order in orders if order["orderStatus"] not in ["Cancelled", "Deactivated"]]
            return JSONResponse(content=filtered_orders, status_code=200)
        else:
            return JSONResponse(content=[], status_code=200)
    except Exception as e:
        logging.error("Error get_orders, {e}")
        return JSONResponse(content={"error": str(e)}, status_code=400)


@app.get("/positions")
async def get_positions(exchange_id: ExchangeID,
                        redis: redis.Redis = Depends(get_redis_client),
                        current_user: User = Depends(security.get_current_user)) -> JSONResponse:
    try:
        positions_data = await get_cache_value("positions", redis, exchange_id)
        if positions_data:
            positions = json.loads(positions_data)
            filtered_positions = [
                position for position in positions
                if position["Buy"]["qty"] != 0 or position["Sell"]["qty"] != 0
            ]
            return JSONResponse(content=filtered_positions, status_code=200)
        else:
            return JSONResponse(content=[], status_code=200)
    except Exception as e:
        logging.error("Error get_positions, {e}")
        return JSONResponse(content={"error": str(e)}, status_code=400)
    
@app.post("/place_order")
async def place_order(order_request: OrderRequest,
                      position_action: PositionAction,
                      exchange_id: ExchangeID,
                      exchange_api: CryptoExchangeAPI = Depends(get_exchange_api),
                      current_user: User = Depends(security.get_current_user),
                      redis:redis.Redis = Depends(get_redis_client)) -> JSONResponse:
    try:
        order_request.orderLinkId = generate_unique_id()

        # Get the relevant RiskLimits item
        risk_limit = await get_risk_limits_for_symbol(order_request.symbol, redis, exchange_id)

        if not risk_limit:
            raise Exception(f"No RiskLimits found for symbol {order_request.symbol}")

        max_leverage = risk_limit.maxLeverage
        order_cost = calculate_order_cost(order_request, max_leverage)
        wallet_balance = await get_wallet_balance(redis, exchange_id)

        if order_cost > wallet_balance.availableBalance:
            raise InsufficientBalanceException(f"Insufficient balance: Required {order_cost}, available {wallet_balance.availableBalance}")

        order_strategy = exchange_api.get_order_strategy()
        # Validate closing position if the position action is close
        if position_action == PositionAction.CLOSE:
            await validate_closing_position(order_request, redis, exchange_id)

        # Modify the order request according to the exchange's API specifications
        modified_order_request = order_strategy.order_builder_factory(order_request, position_action)

        response = await exchange_api.ContractOrder(exchange_api).place_order(modified_order_request)

        if response['retCode'] != 0:
            raise ExchangeAPIException(response['retMsg'])
        
        order_data = {"orderStatus": OrderStatus.PENDING.value, "orderId": response["result"]["orderId"] }
        order_data.update(order_request.dict())
        new_order = Order(**order_data)
        
        # Update WalletBalance
        wallet_balance.positionBalance += order_cost
        wallet_balance.availableBalance -= order_cost
        wallet_balance.walletBalance -= order_cost
        await update_wallet_balance(wallet_balance, redis, exchange_id) 
        await produce_topic_orders_executed(new_order)

        return JSONResponse(content=dict(new_order), status_code=200) 

    except (ExchangeAPIException, InsufficientBalanceException, Exception) as e:
        logging.error(f"Error place_order, {e.__class__.__name__}: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=400)
    
@app.post("/cancel_order/{order_id}")
async def cancel_order(order_id: str,
                    exchange_id: ExchangeID,
                    exchange_api: CryptoExchangeAPI = Depends(get_exchange_api),
                    current_user: User = Depends(security.get_current_user),
                    redis:redis.Redis = Depends(get_redis_client)):
    try:
        return await exchange_api.ContractOrder(exchange_api).cancel_order(order_id)
    except (ExchangeAPIException, Exception) as e:
        logging.error("Error cancel_order, {e}")
        return JSONResponse(content={"error": str(e)}, status_code=400)

#TODO:
@app.post("/set_leverage")
async def set_leverage(leverageRequest: LeverageRequest,
                    exchange_id: ExchangeID,
                    exchange_api: CryptoExchangeAPI = Depends(get_exchange_api),
                    current_user: User = Depends(security.get_current_user),
                    redis:redis.Redis = Depends(get_redis_client)):
    try:
        response = await exchange_api.Position(exchange_api).set_leverage(leverageRequest)
        await set_cache_value(f"Leverage:{leverageRequest.symbol}", leverageRequest.dict(), redis, exchange_id)
        
        return JSONResponse(content={f"Leverage settings for {leverageRequest.symbol} accepted "}, status_code=200)
    except (ExchangeAPIException, Exception) as e:
        logging.error("Error set_leverage, {e}")
        return JSONResponse(content={"error": str(e)}, status_code=400)

@app.post("/set_wallet_balance")
async def set_wallet_balance(walletBalanceRequest: WalletBalanceRequest,
                            exchange_id: ExchangeID,
                            current_user: User = Depends(security.get_current_user),
                            redis:redis.Redis = Depends(get_redis_client)):
    try:
        wallet_balance_key = "wallet_balance"
        wallet_balance_cache = await get_cache_value(wallet_balance_key, redis, exchange_id)
        if wallet_balance_cache:
            wallet_balance = WalletBalance(**json.loads(wallet_balance_cache))
        else:
            raise CachedDataException("No wallet balance found")
        
        if walletBalanceRequest.depositAmt is not None:
            wallet_balance.availableBalance += walletBalanceRequest.depositAmt
            wallet_balance.walletBalance += walletBalanceRequest.depositAmt
        if walletBalanceRequest.withdrawAmt is not None:
            wallet_balance.availableBalance -= walletBalanceRequest.withdrawAmt
            wallet_balance.walletBalance -= walletBalanceRequest.withdrawAmt
        
        await set_cache_value(wallet_balance_key, wallet_balance.dict(), redis, exchange_id)
        return JSONResponse(content=dict(wallet_balance), status_code=200)
        
    except (HTTPException, CachedDataException, Exception) as e:
        logging.error("Error set_wallet_balance, {e}")
        return JSONResponse(content={"error": str(e)}, status_code=400)
        
# ----------------------------- Authentication ---------------------------------

@app.post("/token", response_model=Token)
async def login_for_access_token():
    form_data: OAuth2PasswordRequestForm = Depends()
    user = Security().authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = security.timedelta(minutes=os.environ['ACCESS_TOKEN_EXPIRE_MINUTES'])
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

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

async def send_orders_update(order:str):
    try:
        for websocket in orders_websockets:
            await websocket.send_json(order)
    except Exception as e:
        logging.error(f"Error ws orders update: {e}")

async def send_positions_update(position:str):
    try:
        for websocket in positions_websockets:
            await websocket.send_json(position)
    except Exception as e:
        logging.error(f"Error ws positions update: {e}")

# --------------------------- BACKGROUND TASKS -------------------------------

async def produce_topic_orders_executed(order: Order):
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
            # logging.warning("Starting: consume_topic_orders_resolved")
            
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

async def fetch_orders_history():
    orders_history = []
    consumer = AIOKafkaConsumer(
        "orders",
        bootstrap_servers=os.environ["KAFKA_URI"],
        group_id="orders-history-group",
    )
    await consumer.start()
    try:
        topics = await consumer.topics()
        for tp in topics:
            if tp.startswith("orders"):
                partitions = await consumer.partitions_for_topic(tp)
                for partition in partitions:
                    tp_obj = TopicPartition(tp, partition)
                    earliest_offset = await consumer.beginning_offsets([tp_obj])
                    latest_offset = await consumer.end_offsets([tp_obj])
                    start_offset = earliest_offset[tp_obj]
                    end_offset = latest_offset[tp_obj]

                    await consumer.seek(tp_obj, start_offset)
                    while start_offset < end_offset:
                        messages = await consumer.getmany(timeout_ms=1000)
                        for _, batch in messages.items():
                            for message in batch:
                                orders_history.append(message.value)
                                start_offset += 1
    finally:
        await consumer.stop()
    return orders_history


async def consume_topic_positions_updated(consumer, exit_on_message=False):
    try:
        while True:
            # logging.warning("Starting: consume_positions_updated")
            
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
        self.redis = None
        self.kafka_consumer_orders = None
        self.kafka_consumer_positions = None
        self.kafka_consumer_orders_history = None
        self.kafka_consume_orders_task = None
        self.kafka_consume_positions_task = None

@app.on_event("startup")
async def startup_event():
    try:
        logging.warning("Application startup event")
        app.state = AppState()
        
        app.state.redis = redis.Redis(host=os.environ['REDIS_HOST'], port=os.environ['REDIS_PORT'], db=0)
        
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
    if app.state.redis is not None:
        await app.state.redis.close()        

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