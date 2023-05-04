import pytest
from fastapi import FastAPI
from fastapi.websockets import WebSocket
from fastapi.testclient import TestClient
from httpx import AsyncClient
from ordermanager.app.models.order import OrderRequest, Order, WalletBalance, WalletBalanceRequest, RiskLimit, OrderStatus
from ordermanager.app.models.position import Position
from ordermanager.app.main import app, calculate_order_cost, place_order, set_wallet_balance, User, UserInDB
from unittest.mock import patch, MagicMock, AsyncMock, Mock
import json
import asyncio
import uuid

@pytest.fixture
def test_app() -> FastAPI:
    return app

@pytest.fixture
def test_client(test_app: FastAPI) -> AsyncClient:
    client = TestClient(app=test_app, base_url="http://localhost:8000")
    return client

@pytest.fixture
def test_websocket(test_app: FastAPI) -> WebSocket:
    websocket = WebSocket()
    return websocket

#Stub functions
async def stub_get_wallet_balance():
    return WalletBalance(walletBallance=10000, positionBalance=0, availableBalance=10000)

async def stub_set_wallet_balance(wallet_balance: WalletBalance):
    return

def get_mock_user(payload: dict):
    return User(username="testuser")

def get_mock_user_in_db(payload: dict):
    return UserInDB(username="testuser", hashed_password="testpassword")


@pytest.fixture
async def jwt_token(test_client: TestClient, monkeypatch):
    # Stub the authenticate_user function
    monkeypatch.setattr("ordermanager.app.main.security.authenticate_user", get_mock_user({"username": "testuser"}))

    test_credentials = {"username": "testuser", "password": "testpassword"}
    response = await test_client.post("/token", data=test_credentials)
    assert response.status_code == 200
    token = response.json().get("access_token")
    return token

# Test placing an order with sufficient balance
@pytest.mark.asyncio
async def test_place_order_sufficient_balance(jwt_token):
    order_request = OrderRequest(
        symbol="BTCUSDT",
        side="Buy",
        orderType="Limit",
        qty="0.4",
        price="25000",
        timeInForce="GoodTillCancel",   
    )

    mock_risk_limit = RiskLimit(
        id="1",
        symbol="BTCUSDT",
        maxLeverage="20",
        isLowestRiskLimit="1",
        initialMargin=".1",
        maintenanceMargin=".05",
        riskLimitValue="10000",
    )

    def mock_get_wallet_balance(key: str):
        return starting_wallet_balance
        
    def mock_get_risk_limits(key:str):
        return mock_risk_limit
    
    orderLinkId = str(uuid.uuid4())
    orderId = '123456'
    mock_bybit_api_response = {"retCode": 0, "result": {'orderId': orderId, 'orderLinkId': orderLinkId }}
    
    starting_amt = 10000
    starting_wallet_balance = WalletBalance(walletBalance=starting_amt, positionBalance=0, availableBalance=starting_amt)
    order_cost = calculate_order_cost(order_request, mock_risk_limit.maxLeverage)
    ending_amt = starting_amt - order_cost
    ending_wallet_balance = WalletBalance(walletBalance=ending_amt, positionBalance=order_cost, availableBalance=ending_amt)

    with patch("ordermanager.app.main.api.ContractOrder.place_order", return_value=mock_bybit_api_response), \
        patch("uuid.uuid4", return_value=uuid.UUID(orderLinkId)), \
        patch("ordermanager.app.main.get_risk_limits", new_callable=AsyncMock, side_effect=mock_get_risk_limits), \
        patch("ordermanager.app.main.produce_topic_orders_executed", new_callable=AsyncMock, return_value=None) as order_producer, \
        patch("ordermanager.app.main.get_wallet_balance", new_callable=AsyncMock, side_effect=mock_get_wallet_balance), \
        patch("ordermanager.app.main.update_wallet_balance",new_callable=AsyncMock, return_value=None) as update_wallet_balance:
            
            response = await place_order(order_request, jwt_token)

            # assert wallet balance was updated upon successful order placement
            update_wallet_balance.assert_called_with(ending_wallet_balance)

            # assert order correct Order values were sent to the producer
            order_data = {'orderId': orderId, 'orderStatus': OrderStatus.PENDING.value}
            order_data.update(order_request.dict())
            order_to_topic = Order(**order_data)
            order_producer.assert_called_with(order_to_topic)

            # order_producer.assert_called_with(order_to_topic)
            assert response["retCode"] == 0
            assert response["result"]["orderLinkId"] == mock_bybit_api_response["result"]["orderLinkId"]
                

# Test placing an order with insufficient balance (expect an InsufficientBalanceException)
@pytest.mark.asyncio
async def test_place_order_insufficient_balance(jwt_token):
    order_request = OrderRequest(
        symbol="BTCUSDT",
        side="Buy",
        orderType="Limit",
        qty="5",
        price="25000",
        timeInForce="GoodTillCancel",   
    )

    mock_risk_limit = RiskLimit(
        id="1",
        symbol="BTCUSDT",
        maxLeverage="20",
        isLowestRiskLimit="1",
        initialMargin=".1",
        maintenanceMargin=".05",
        riskLimitValue="10000",
    )

    def mock_get_wallet_balance(key: str):
        return starting_wallet_balance
        
    def mock_get_risk_limits(key:str):
        return mock_risk_limit
        
    mock_bybit_api_response = {"retCode": 0, "result": {"orderId": "332561", "orderLinkId": "11111"}}

    starting_amt = 3000
    starting_wallet_balance = WalletBalance(walletBalance=starting_amt, positionBalance=0, availableBalance=starting_amt)
    
    with patch("ordermanager.app.main.api.ContractOrder.place_order", return_value=mock_bybit_api_response), \
        patch("ordermanager.app.main.get_risk_limits", side_effect=mock_get_risk_limits), \
        patch("ordermanager.app.main.produce_topic_orders_executed", return_value=None), \
        patch("ordermanager.app.main.get_wallet_balance", side_effect=mock_get_wallet_balance), \
        patch("ordermanager.app.main.update_wallet_balance", return_value=None):        
            error_message = await place_order(order_request, jwt_token)
            assert error_message == {'error': 'Insufficient balance: Required 6681.25, available 3000.0'}


# Place an order with insufficient balance. Expect an InsufficientBalanceException
# Reload the wallet and place the second order again. Expect the second order to be placed.
test_data = [
    (
     OrderRequest(
        symbol="BTCUSDT",
        side="Buy",
        orderType="Limit",
        qty="5",
        price="25000",
        timeInForce="GoodTillCancel",   
    ),
    WalletBalance(walletBalance=6000, positionBalance=0, availableBalance=6000),
    RiskLimit(
        id="1",
        symbol="BTCUSDT",
        maxLeverage="20",
        isLowestRiskLimit="1",
        initialMargin=".1",
        maintenanceMargin=".05",
        riskLimitValue="10000",
    )
)
]
@pytest.mark.parametrize("order_request, starting_wallet_balance, mock_risk_limit", test_data)
@pytest.mark.asyncio
async def test_place_order_multiple_orders_wallet_reload(order_request, starting_wallet_balance, mock_risk_limit, jwt_token):
   
    def mock_get_risk_limits_for_symbol(symbol: str):
        if symbol is order_request.symbol:
            return mock_risk_limit
        else:
            return None
        
    orderLinkId = str(uuid.uuid4())
    orderId = 'RandomOrderId'
    mock_bybit_api_response = {"retCode": 0, "result": {'orderId': orderId, 'orderLinkId': orderLinkId }}
    order_cost = calculate_order_cost(order_request, mock_risk_limit.maxLeverage)    
    
    with patch("ordermanager.app.main.api.ContractOrder.place_order", return_value=mock_bybit_api_response), \
            patch("uuid.uuid4", return_value=uuid.UUID(orderLinkId)), \
            patch("ordermanager.app.main.get_risk_limits_for_symbol", new_callable=AsyncMock, side_effect=mock_get_risk_limits_for_symbol), \
            patch("ordermanager.app.main.produce_topic_orders_executed", new_callable=AsyncMock, return_value=None) as order_producer, \
            patch("ordermanager.app.main.get_wallet_balance", new_callable=AsyncMock, return_value=starting_wallet_balance):
            # patch("ordermanager.app.main.update_wallet_balance",new_callable=AsyncMock, return_value=None) as update_wallet_balance:
            error_message = await place_order(order_request, jwt_token)
            assert error_message == {'error': 'Insufficient balance: Required 6681.25, available 6000.0'}
    
   
    
    # Send a wallet reload request to '/set_wallet_balance' to meet minimum balance requirement for order
    def mock_set_cache_value(key: str, value: WalletBalance): return None

    with patch("ordermanager.app.main.get_cache_value", new_callable=AsyncMock, return_value=starting_wallet_balance.json()) as get_cache_value, \
        patch("ordermanager.app.main.set_cache_value", new_callable=AsyncMock, side_effect=mock_set_cache_value) as set_cache_value:

        # Add minimum amount to wallet to cover order cost
        amt_to_add = order_cost - starting_wallet_balance.availableBalance
        new_wallet_balance = WalletBalance(walletBalance=starting_wallet_balance.walletBalance + amt_to_add, positionBalance=0, availableBalance=starting_wallet_balance.availableBalance + amt_to_add)

        wallet_balance_cache_key = "wallet_balance"

        # Send a wallet reload request to '/set_wallet_balance'
        wb_request = WalletBalanceRequest(depositAmt=amt_to_add, withdrawAmt=0)
        response = await set_wallet_balance(wb_request, jwt_token)

        # assert get_cache_value() within set_wallet_balance() is called with the correct cache key
        get_cache_value.assert_called_once_with(wallet_balance_cache_key)

        # assert set_cache_value() within set_wallet_balance() is called with the correct cache key and values as computed on starting_wallet_balance
        set_cache_value.assert_called_once_with(wallet_balance_cache_key, new_wallet_balance.dict())

        # assert correct balance is returned from set_wallet_balance()
        assert response == new_wallet_balance
        
    # Place the order again. Expect the order to be placed.
    def mock_update_wallet_balance(wallet_balance: WalletBalance):
        return 

    with patch("ordermanager.app.main.api.ContractOrder.place_order", return_value=mock_bybit_api_response), \
        patch("ordermanager.app.main.get_risk_limits_for_symbol", new_callable=AsyncMock, side_effect=mock_get_risk_limits_for_symbol), \
        patch("uuid.uuid4", return_value=uuid.UUID(orderLinkId)), \
        patch("ordermanager.app.main.produce_topic_orders_executed", new_callable=AsyncMock, return_value=None) as order_producer, \
        patch("ordermanager.app.main.get_wallet_balance", new_callable=AsyncMock, return_value=new_wallet_balance) as get_wallet_balance, \
        patch("ordermanager.app.main.update_wallet_balance",new_callable=AsyncMock, side_effect=mock_update_wallet_balance) as update_wallet_balance:
        response = await place_order(order_request, jwt_token)
        
        get_wallet_balance.assert_called_once_with(wallet_balance_cache_key)
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
        update_wallet_balance.assert_called_once_with(new_wallet_balance)

        # assert order was successfully placed in Bybit
        assert response["retCode"] == 0
        assert response["result"]["orderLinkId"] == mock_bybit_api_response["result"]["orderLinkId"]


# ------------Test WebSocket connections ----------------

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
    
    with client.websocket_connect("/ws/positions") as websocket:
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
    
    with client.websocket_connect("/ws/orders") as websocket:
        # Send the position message via websocket
        # Wait for a response
        received_position_text = websocket.receive_text()
        # Compare the sent and received positions
        assert order.json() == received_position_text