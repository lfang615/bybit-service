from fastapi import FastAPI, WebSocket, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from starlette.websockets import WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from bson.json_util import dumps
from ordermanager.app.bybit import BybitAPI, BybitAPIException
from ordermanager.app.security import Security, User, UserInDB, Token, TokenData
from ordermanager.app.models.order import *
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
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
from jose import JWTError, jwt

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


def generate_unique_id():
    return str(uuid.uuid4())


# ------------------------- CUSTOM EXCEPTIONS ---------------------------------
class InsufficientBalanceException(Exception):
    pass

class CachedDataException(Exception):
    pass

#------------------------- REST API ---------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_vue_app(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logging.error("Error serve_vue_app, {e}")
        return HTMLResponse(status_code=404)
    
@app.get("/symbols")
async def get_symbols():
    try:
        result = await app.state.redis.hgetall("symbols")

        decoded_result = [v.decode("utf-8") for k, v in result.items()]
        return decoded_result
    except (BybitAPIException, HTTPException, Exception) as e:
        logging.error("Error get_symbols, {e}")
        return {"error": str(e)}

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
    except (BybitAPIException, HTTPException) as e:
        logging.error("Error get_order, {e}")
        return {"error": str(e)}

@app.get("/orders")
async def get_orders():
    try:
        orders_data = await get_cache_value("orders")
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
        positions_data = await get_cache_value("positions")
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
async def place_order(order_request: OrderRequest,
                      current_user: User = Depends(security.get_current_user)):
    try:
        order_request.orderLinkId = generate_unique_id()

        # Get the relevant RiskLimits item
        risk_limit = await get_risk_limits_for_symbol(order_request.symbol)

        if not risk_limit:
            raise Exception(f"No RiskLimits found for symbol {order_request.symbol}")

        max_leverage = risk_limit.maxLeverage
        order_cost = calculate_order_cost(order_request, max_leverage)
        wallet_balance = await get_wallet_balance("wallet_balance")

        if order_cost > wallet_balance.availableBalance:
            raise InsufficientBalanceException(f"Insufficient balance: Required {order_cost}, available {wallet_balance.availableBalance}")

        response = await api.ContractOrder(api).place_order(order_request)

        if response['retCode'] == 0:
            order_data = {"orderStatus": OrderStatus.PENDING.value, "orderId": response["result"]["orderId"], }
            order_data.update(order_request.dict())
            order_data = Order(**order_data)
            
            # Update WalletBalance
            wallet_balance.positionBalance += order_cost
            wallet_balance.availableBalance -= order_cost
            wallet_balance.walletBalance -= order_cost
            await update_wallet_balance(wallet_balance) 

            await produce_topic_orders_executed(order_data)

        return response

    except (BybitAPIException, InsufficientBalanceException, Exception) as e:
        logging.error(f"Error place_order, {e.__class__.__name__}: {e}")
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
    
@app.post("/set_wallet_balance")
async def set_wallet_balance(walletBalanceRequest: WalletBalanceRequest,
                             current_user: User = Depends(security.get_current_user)):
    try:
        wallet_balance_key = "wallet_balance"
        wallet_balance_cache = await get_cache_value(wallet_balance_key)
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
        
        await set_cache_value(wallet_balance_key, wallet_balance.dict())
        return wallet_balance
        
    except (HTTPException, CachedDataException, Exception) as e:
        logging.error("Error set_wallet_balance, {e}")
        return {"error": str(e)}
    
# ------------------------UTILITY FUNCTIONS -----------------------------
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


async def update_wallet_balance(wallet_balance: WalletBalance):
    try:
        wallet_balance_key = "wallet_balance"
        await set_cache_value(wallet_balance_key, wallet_balance.dict())
    except Exception as e:
        logging.error(f"Error update_wallet_balance, {e}")
        raise e


async def get_wallet_balance() -> WalletBalance:
    try:
        wallet_balance_data = await get_cache_value("wallet_balance")
        if wallet_balance_data:
            wallet_balance = WalletBalance(**json.loads(wallet_balance_data))
            return wallet_balance
        else:
            return WalletBalance()
    except Exception as e:
        logging.error("Error get_wallet_balance, {e}")
        return {"error": str(e)}


async def get_risk_limits_for_symbol(symbol:str) -> RiskLimit:
    try:
        risk_limit_data = await get_cache_value(f"risk_limits:{symbol}")
        if risk_limit_data:
            risk_limits = RiskLimit(**json.loads(risk_limit_data))
            return risk_limits
        else:
            raise CachedDataException("No cached data for risk limits")
    except Exception as e:
        logging.error("Error get_risk_limits_for_symbol, {e}")
        return {"error": str(e)}
    

async def get_cache_value(key: str):
    try:        
        data = await app.state.redis.get(key)
        if data:
            return data
        else:
            return None
    except Exception as e:
        logging.error(f"Error get_from_redis_cache, {e}")
        raise e
    
async def set_cache_value(key: str, data: dict):
    try:        
        await app.state.redis.set(key, json.dumps(data))
    except Exception as e:
        logging.error(f"Error set_cache_value, {e}")
        raise e
    
    
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


async def consume_topic_positions_updated(consumer, exit_on_message=False):
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
        self.redis = None
        self.kafka_consumer_orders = None
        self.kafka_consumer_positions = None
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