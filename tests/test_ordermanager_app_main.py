import pytest
from fastapi import FastAPI, HTTPException
from fastapi.websockets import WebSocket
from fastapi.testclient import TestClient
from httpx import AsyncClient
from ordermanager.app.models.order import OrderRequest, Order, WalletBalance, WalletBalanceRequest, \
    RiskLimit, OrderStatus, OrderSide, OrderType, TimeInForce, PositionAction, ExchangeID
from ordermanager.app.models.position import Position
from ordermanager.app.services.cryptoexchangeapi import CryptoExchangeAPI
from ordermanager.app.services.bybitorderstrategy import OrderStrategy, BybitOrderStrategy
from ordermanager.app.main import app, User, calculate_order_cost, place_order, set_wallet_balance, get_wallet_balance, \
    crypto_exchange_factory, get_exchange_api
from ordermanager.app.services.bybit import BybitAPI
from unittest.mock import patch, MagicMock, AsyncMock
from ordermanager.app.exceptions import InvalidOrderTypeException
import json
from typing import Dict
import uuid
import redis.asyncio as redis
import os
from dotenv import load_dotenv
from ordermanager.app.utils import validate_closing_position

load_dotenv()

@pytest.fixture
def test_app() -> FastAPI:
    return app

@pytest.fixture
def test_client(test_app: FastAPI) -> AsyncClient:
    client = TestClient(app=test_app, base_url=os.getenv("ORDER_MANAGER_URI"))
    return client

@pytest.fixture
def test_websocket(test_app: FastAPI) -> WebSocket:
    websocket = WebSocket()
    return websocket

@pytest.fixture
def mock_redis(monkeypatch):
    redis_mock = MagicMock(spec=redis.Redis)
    monkeypatch.setattr("ordermanager.app.main.get_redis_client", redis_mock)
    return redis_mock


@pytest.fixture
def mock_redis_client_factory(monkeypatch, mock_redis):
    async def _mock_redis_client(data: Dict[str, str], exchange_id: ExchangeID):
        monkeypatch.setattr("ordermanager.app.services.bybitorderstrategy.redis", mock_redis)
        mock_redis.get.side_effect = AsyncMock(side_effect=lambda key: data.get(f"{exchange_id}:{key.decode('utf-8')}"))
        mock_redis.set.side_effect = AsyncMock(side_effect=lambda key, value: data.update({f"{exchange_id}:{key.decode('utf-8')}": value}))
        
        return mock_redis

    return _mock_redis_client


@pytest.fixture
def mock_risk_limits_data():
     return RiskLimit(  
            id="1",
            symbol="BTCUSDT",
            maxLeverage="20",
            isLowestRisk="1",
            initialMargin=".1",
            maintainMargin=".05",
            limit="10000")

def get_mock_user(payload: dict):
    return User(username="testuser")


@pytest.fixture
async def jwt_token(test_client: TestClient, monkeypatch):
    # Stub the authenticate_user function
    monkeypatch.setattr("ordermanager.app.main.security.authenticate_user", get_mock_user({"username": "testuser"}))

    test_credentials = {"username": "testuser", "password": "testpassword"}
    response = await test_client.post("/token", data=test_credentials)
    assert response.status_code == 200
    token = response.json().get("access_token")
    return token


"""
BybitAPI and BybitOrderStrategy mocks
"""
@pytest.fixture
def mock_order_data():
    orderLinkId = str(uuid.uuid4())
    orderId = '123456'
    mock_bybit_api_response = {"retCode": 0, "result": {'orderId': orderId, 'orderLinkId': orderLinkId }}
    sufficient_start_amt = 10000
    insufficient_start_amt = 3000

    return orderLinkId, orderId, mock_bybit_api_response, sufficient_start_amt, insufficient_start_amt

@pytest.fixture
def mock_bybit_order_strategy():
    mock_strategy = MagicMock(spec=OrderStrategy)
    mock_strategy.order_builder_factory.return_value = BybitOrderStrategy()
    return mock_strategy

@pytest.fixture
def mock_bybit_exchange_api(mock_bybit_order_strategy, mock_order_data):
    mock_api = MagicMock(spec=CryptoExchangeAPI)
    mock_api.get_order_strategy.return_value = mock_bybit_order_strategy
    
    _, _, mock_bybit_api_response, _, _ = mock_order_data
    
    async def mock_api_contractorder_placeorder(*args, **kwargs):
        return mock_bybit_api_response  # return the mocked API response

    mock_api.ContractOrder.return_value.place_order = mock_api_contractorder_placeorder
    return mock_api


"""
Assert correct values are set for Bybit ordering API when using BybitOrderStrategy
"""
@pytest.fixture
def bybit_order_strategy():
    return BybitOrderStrategy()

@pytest.fixture
def bybit_strategy_order_request():
    return OrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.BUY.value,
        orderType=OrderType.LIMIT.value,
        qty=1,
        price=10000,
        triggerPrice=9000,
        timeInForce=TimeInForce.GTC.value,
    )

def test_build_open_limit_order(bybit_order_strategy, bybit_strategy_order_request):
    result = bybit_order_strategy.build_open_limit_order(bybit_strategy_order_request)
    assert result.reduceOnly == False

def test_build_close_limit_order(bybit_order_strategy, bybit_strategy_order_request):
    result = bybit_order_strategy.build_close_limit_order(bybit_strategy_order_request)
    assert result.reduceOnly == True
    assert result.positionIdx == 1

def test_build_open_market_order(bybit_order_strategy, bybit_strategy_order_request):
    result = bybit_order_strategy.build_open_market_order(bybit_strategy_order_request)
    assert result.orderType == OrderType.MARKET.value
    assert result.reduceOnly == False

def test_build_close_market_order(bybit_order_strategy, bybit_strategy_order_request):
    result = bybit_order_strategy.build_close_market_order(bybit_strategy_order_request)
    assert result.orderType == OrderType.MARKET.value
    assert result.reduceOnly == True
    assert result.positionIdx == 1
    assert result.closeOnTrigger == True

def test_build_open_stop_market_order(bybit_order_strategy, bybit_strategy_order_request):
    result = bybit_order_strategy.build_open_stop_market_order(bybit_strategy_order_request)
    assert result.orderType == OrderType.MARKET.value
    assert result.reduceOnly == False
    assert result.triggerDirection == 1

def test_build_close_stop_market_order(bybit_order_strategy, bybit_strategy_order_request):
    result = bybit_order_strategy.build_close_stop_market_order(bybit_strategy_order_request)
    assert result.orderType == OrderType.MARKET.value
    assert result.reduceOnly == True
    assert result.triggerDirection == 1
    assert result.positionIdx == 1

def test_build_open_stop_limit_order(bybit_order_strategy, bybit_strategy_order_request):
    result = bybit_order_strategy.build_open_stop_limit_order(bybit_strategy_order_request)
    assert result.orderType == OrderType.LIMIT.value
    assert result.reduceOnly == False
    assert result.triggerDirection == 1

def test_build_close_stop_limit_order(bybit_order_strategy, bybit_strategy_order_request):
    result = bybit_order_strategy.build_close_stop_limit_order(bybit_strategy_order_request)
    assert result.orderType == OrderType.LIMIT.value
    assert result.reduceOnly == True
    assert result.triggerDirection == 1
    assert result.positionIdx == 1
    assert result.closeOnTrigger == True

"""
End BybitOrderStrategy tests
"""

def test_crypto_exchange_factory_bybit():
    api_key = "test_api_key"
    secret_key = "test_secret_key"

    result = crypto_exchange_factory(api_key, secret_key, ExchangeID.BYBIT)
    assert isinstance(result, BybitAPI)

def test_crypto_exchange_factory_unsupported_exchange():
    api_key = "test_api_key"
    secret_key = "test_secret_key"

    with pytest.raises(ValueError):
        crypto_exchange_factory(api_key, secret_key, "unsupported_exchange")

@pytest.mark.asyncio
async def test_get_exchange_api_valid_keys(mocker, jwt_token):
    api_key = "test_api_key"
    secret_key = "test_secret_key"

    # Mock the os.getenv function to return the test API keys
    mocker.patch.dict(os.environ, {
        "BYBIT_API_KEY": api_key,
        "BYBIT_SECRET_KEY": secret_key
    })

    result = await get_exchange_api(ExchangeID.BYBIT, jwt_token)
    assert isinstance(result, CryptoExchangeAPI)

@pytest.mark.asyncio
async def test_get_exchange_api_missing_keys(mocker, jwt_token):
    # Clear the test API keys from the environment
    mocker.patch.dict(os.environ, {
        "BYBIT_API_KEY": "",
        "BYBIT_SECRET_KEY": ""
    })

    with pytest.raises(HTTPException) as exc_info:
        await get_exchange_api(ExchangeID.BYBIT, jwt_token)

    assert exc_info.value.status_code == 400
    assert "API keys not found for exchange" in exc_info.value.detail


@pytest.fixture
def mock_position():
    mock_position = Position(
        symbol="BTCUSDT",
        side=OrderSide.SELL.value,
        openDate="01/01/2023 00:00",
        qty=100,
        aep=20000,
        linkedOrders=[
            Order(
                symbol="BTCUSDT",
                side=OrderSide.SELL.value,
                orderType="Limit",
                price="20000",
                qty="100",
                orderLinkId="123456",
                orderStatus="Filled",
                orderId="123",
                timeInForce="GoodTillCancel",
                cumExecQty="1",
                reduceOnly=False
            )
        ]
    )
    return mock_position.json()

@pytest.mark.asyncio
async def test_validate_closing_position_valid(mock_position):
    # setup
    mock_redis = AsyncMock(spec=redis.Redis)

    
    mock_data = {
        "BYBIT:position:BTCUSDT:Sell": mock_position
    }

    mock_redis.get = AsyncMock(side_effect=lambda key: mock_data.get(key))

    order_request = OrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.BUY.value,
        orderType=OrderType.LIMIT.value,
        qty=50,
        price=10000,
        timeInForce="GoodTillCancel"
    )

    # action
    position = await validate_closing_position(order_request, mock_redis, ExchangeID.BYBIT)

    # assert
    assert position.symbol == "BTCUSDT"
    assert position.side == "Sell"
    assert position.qty == 100


@pytest.mark.asyncio
async def test_validate_closing_position_invalid(mock_position):
    # setup
    mock_redis = MagicMock(spec=redis.Redis)
    mock_data = {
        "BYBIT:position:BTCUSDT:Sell": mock_position
    }

    mock_redis.get = AsyncMock(side_effect=lambda key: mock_data.get(key))

    order_request = OrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.SELL.value,
        orderType=OrderType.LIMIT.value,
        qty=50,
        price=10000,
        timeInForce="GoodTillCancel"
    )

    # action and assert
    with pytest.raises(InvalidOrderTypeException, match="No position to close"):
        await validate_closing_position(order_request, mock_redis, ExchangeID.BYBIT)


# Test placing an order with sufficient balance
@pytest.mark.asyncio
async def test_place_order_sufficient_balance(
        jwt_token, mock_redis, mock_order_data, mock_risk_limits_data, mock_bybit_exchange_api):

    order_request = OrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.BUY.value,
        orderType=OrderType.LIMIT.value,
        qty="0.4",
        price="25000",
        timeInForce="GoodTillCancel",   
    )

    # Unpack the mock_order_data fixture
    orderLinkId, orderId, mock_bybit_api_response, sufficient_start_amt, _ = mock_order_data

    starting_wallet_balance = WalletBalance(walletBalance=sufficient_start_amt, positionBalance=0, availableBalance=sufficient_start_amt)
    order_cost = calculate_order_cost(order_request, mock_risk_limits_data.maxLeverage)
    ending_amt = sufficient_start_amt - order_cost
    ending_wallet_balance = WalletBalance(walletBalance=ending_amt, positionBalance=order_cost, availableBalance=ending_amt)

  
    with patch("ordermanager.app.main.update_wallet_balance", return_value=None) as mock_update_wallet_balance, \
        patch("ordermanager.app.main.get_wallet_balance", new_callable=AsyncMock, return_value=starting_wallet_balance), \
        patch("ordermanager.app.main.get_risk_limits_for_symbol", return_value=mock_risk_limits_data), \
        patch("uuid.uuid4", return_value=uuid.UUID(orderLinkId)), \
        patch("ordermanager.app.main.produce_topic_orders_executed", new_callable=AsyncMock, return_value=None) as order_producer:
            response = await place_order(order_request, PositionAction.OPEN, ExchangeID.BYBIT, mock_bybit_exchange_api, jwt_token, mock_redis)

            # assert wallet balance was updated upon successful order placement
            mock_update_wallet_balance.assert_called_with(ending_wallet_balance, mock_redis, ExchangeID.BYBIT)

            # assert order correct Order values were sent to the producer
            order_data = {'orderId': orderId, 'orderStatus': OrderStatus.PENDING.value}
            order_data.update(order_request.dict())
            order_to_topic = Order(**order_data)
            order_producer.assert_called_with(order_to_topic)

            assert response.status_code == 200
            assert json.loads(response.body)['orderLinkId'] == mock_bybit_api_response["result"]["orderLinkId"]
                

# Test placing an order with insufficient balance (expect an InsufficientBalanceException)
@pytest.mark.asyncio
async def test_place_order_insufficient_balance( jwt_token, mock_redis, mock_order_data, mock_risk_limits_data, mock_bybit_exchange_api):
    order_request = OrderRequest(
        symbol="BTCUSDT",
        side="Buy",
        orderType="Limit",
        qty="5",
        price="25000",
        timeInForce="GoodTillCancel",   
    )

     # Unpack the mock_order_data fixture
    _, _, _, _, insufficient_start_amt = mock_order_data
    
    starting_wallet_balance = WalletBalance(walletBalance=insufficient_start_amt, positionBalance=0, availableBalance=insufficient_start_amt)
    
    with patch("ordermanager.app.main.get_risk_limits_for_symbol", return_value=mock_risk_limits_data), \
        patch("ordermanager.app.main.produce_topic_orders_executed", return_value=None), \
        patch("ordermanager.app.main.get_wallet_balance", new_callable=AsyncMock, return_value=starting_wallet_balance), \
        patch("ordermanager.app.main.update_wallet_balance", return_value=None):
            error_message = await place_order(order_request, PositionAction.OPEN, ExchangeID.BYBIT, mock_bybit_exchange_api, jwt_token, mock_redis)
            assert json.loads(error_message.body)['error'] == 'Insufficient balance: Required 6681.25, available 3000.0'


# Place an order with insufficient balance. Expect an InsufficientBalanceException
# Reload the wallet and place the second order again. Expect the second order to be placed.
@pytest.mark.asyncio
async def test_place_order_multiple_orders_wallet_reload(jwt_token, mock_redis, mock_risk_limits_data, mock_bybit_exchange_api, mock_order_data):
    
    order_request = OrderRequest(
        symbol="BTCUSDT",
        side="Buy",
        orderType="Limit",
        qty="5",
        price="25000",
        timeInForce="GoodTillCancel",   
    )
    
    orderLinkId, orderId, mock_bybit_api_response, _, insufficient_start_amt = mock_order_data
    starting_wallet_balance = WalletBalance(walletBalance=insufficient_start_amt, positionBalance=0, availableBalance=insufficient_start_amt)
    order_cost = calculate_order_cost(order_request, mock_risk_limits_data.maxLeverage)    
    
    with patch("uuid.uuid4", return_value=uuid.UUID(orderLinkId)), \
        patch("ordermanager.app.main.get_risk_limits_for_symbol", return_value=mock_risk_limits_data), \
        patch("ordermanager.app.main.produce_topic_orders_executed", new_callable=AsyncMock, return_value=None) as order_producer, \
        patch("ordermanager.app.main.get_wallet_balance", new_callable=AsyncMock, return_value=starting_wallet_balance):
            error_message = await place_order(order_request, PositionAction.OPEN, ExchangeID.BYBIT, mock_bybit_exchange_api, jwt_token, mock_redis)
            assert json.loads(error_message.body)['error'] == 'Insufficient balance: Required 6681.25, available 3000.0'
    
    #Send a wallet reload request to '/set_wallet_balance' to meet minimum balance requirement for order
    def mock_set_cache_value(key: str, value: WalletBalance, mock_redis): return None

    with patch("ordermanager.app.main.get_cache_value", new_callable=AsyncMock, return_value=starting_wallet_balance.json()) as get_cache_value, \
        patch("ordermanager.app.main.set_cache_value", new_callable=AsyncMock, return_value=None) as set_cache_value:

        # Add minimum amount to wallet to cover order cost
        amt_to_add = order_cost - starting_wallet_balance.availableBalance
        new_wallet_balance = WalletBalance(walletBalance=starting_wallet_balance.walletBalance + amt_to_add, positionBalance=0, availableBalance=starting_wallet_balance.availableBalance + amt_to_add)

        wallet_balance_cache_key = "wallet_balance"

        # Send a wallet reload request to '/set_wallet_balance'
        wb_request = WalletBalanceRequest(depositAmt=amt_to_add, withdrawAmt=0)
        response = await set_wallet_balance(wb_request, ExchangeID.BYBIT, jwt_token, mock_redis)

        # assert get_cache_value() within set_wallet_balance() is called with the correct cache key
        get_cache_value.assert_called_once_with(wallet_balance_cache_key, mock_redis, ExchangeID.BYBIT)

        # assert set_cache_value() within set_wallet_balance() is called with the correct cache key and values as computed on starting_wallet_balance
        set_cache_value.assert_called_once_with(wallet_balance_cache_key, new_wallet_balance.dict(), mock_redis, ExchangeID.BYBIT)

        # assert correct balance is returned from set_wallet_balance()
        assert WalletBalance(**json.loads(response.body)) == new_wallet_balance
        
    # # Place the order again. Expect the order to be placed.
    # # def mock_update_wallet_balance(wallet_balance: WalletBalance, mock_redis):
    # #     return 

    with patch("ordermanager.app.main.get_risk_limits_for_symbol", return_value=mock_risk_limits_data), \
        patch("uuid.uuid4", return_value=uuid.UUID(orderLinkId)), \
        patch("ordermanager.app.main.produce_topic_orders_executed", new_callable=AsyncMock, return_value=None) as order_producer, \
        patch("ordermanager.app.main.get_wallet_balance", new_callable=AsyncMock, return_value=new_wallet_balance) as get_wallet_balance, \
        patch("ordermanager.app.main.update_wallet_balance",new_callable=AsyncMock, return_value=None) as update_wallet_balance:
        place_order_success = await place_order(order_request, PositionAction.OPEN, ExchangeID.BYBIT, mock_bybit_exchange_api, jwt_token, mock_redis)
         # assert order was successfully placed in Bybit
        assert place_order_success.status_code == 200
        assert json.loads(place_order_success.body)["orderLinkId"] == mock_bybit_api_response["result"]["orderLinkId"]

        get_wallet_balance.assert_called_once_with(mock_redis, ExchangeID.BYBIT)
        # Assert the values in new_wallet_balance have been adjusted to reflect the order cost
        assert new_wallet_balance.availableBalance == 0
        assert new_wallet_balance.walletBalance == 0
        assert new_wallet_balance.positionBalance == order_cost
        
        # assert correct values are loaded into Order and sent to the orders_executed topic
        order_data = {'orderId': orderId, 'orderStatus': OrderStatus.PENDING.value}
        order_data.update(order_request.dict())
        order_to_topic = Order(**order_data)
        order_producer.assert_called_with(order_to_topic)

        # Assert that update_wallet_balance is saving the new balance to the cache with the correct values
        update_wallet_balance.assert_called_once_with(new_wallet_balance, mock_redis, ExchangeID.BYBIT)

       


"""
Test WebSocket connections
"""

@pytest.mark.asyncio
async def test_send_positions_update():
    position = Position(
        symbol="BTCUSDT",
        side="Sell",
        openDate="01/01/2023 00:00",
        qty=1,
        aep=20000,
        linkedOrders=[
            Order(
                symbol="BTCUSDT",
                side="Sell",
                orderType="Limit",
                price="20000",
                qty="1",
                orderLinkId="123456",
                orderStatus="Filled",
                orderId="123",
                timeInForce="GoodTillCancel",
                cumExecQty="1",
                reduceOnly=False
            )
        ]
    )  

    async def app(scope, receive, send):
        assert scope['type'] == 'websocket'
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        await websocket.send_text(position.json())
        await websocket.close()

    client = TestClient(app)

    headers = {
        "Authorization": f"Bearer {jwt_token}",
    }
    
    with client.websocket_connect("/ws/positions", headers=headers) as websocket:
        # Send the position message via websocket
        # Wait for a response
        received_position_text = websocket.receive_text()
        # Compare the sent and received positions
        assert position.json() == received_position_text


@pytest.mark.asyncio
async def test_send_orders_update():
    order = Order(
                symbol="BTCUSDT",
                side="Sell",
                orderType="Limit",
                price="20000",
                qty="1",
                orderLinkId="123456",
                orderStatus="Filled",
                orderId="123",
                timeInForce="GoodTillCancel",
                cumExecQty="1",
                reduceOnly=False
            )

    async def app(scope, receive, send):
        assert scope['type'] == 'websocket'
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        await websocket.send_text(order.json())
        await websocket.close()

    client = TestClient(app)

    headers = {
        "Authorization": f"Bearer {jwt_token}",
    }
    
    with client.websocket_connect("/ws/orders", headers=headers) as websocket:
        # Send the position message via websocket
        # Wait for a response
        received_position_text = websocket.receive_text()
        # Compare the sent and received positions
        assert order.json() == received_position_text