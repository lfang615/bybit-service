import pytest
from .conftest import test_client
from ordermanager.app.models.order import OrderRequest
from .mockclasses import *
from ordermanager.app.main import calculate_order_cost, place_order, User, UserInDB
from unittest.mock import patch, MagicMock


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
async def jwt_token(test_client, monkeypatch):
    # Stub the authenticate_user function
    monkeypatch.setatr("ordermanager.app.main.security.authenticate_user", get_mock_user({"username": "testuser"}))
    
    async with test_client as client:
        test_credentials = {"username": "testuser", "password": "testpassword"}
        response = await client.post("/token", data=test_credentials)
        assert response.status_code == 200
        token = response.json().get("access_token")
        return token

# Test placing an order with sufficient balance
@pytest.mark.asyncio
async def test_place_order_sufficient_balance(jwt_token):
    headers = {"Authorization": f"Bearer {jwt_token}"}
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

    def mock_get_cache_value(key: str):
        if key.startswith("risk_limits"):
            return mock_risk_limit
        elif key == "wallet_balance":
            return starting_wallet_balance
        else:
            return None
        
    mock_bybit_api_response = {"retCode": 0, "result": {"orderId": "332561", "orderLinkId": "11111"}}

    starting_amt = 10000
    starting_wallet_balance = WalletBalance(walletBalance=starting_amt, positionBalance=0, availableBalance=starting_amt)
    order_cost = calculate_order_cost(order_request, mock_risk_limit.maxLeverage)
    ending_amt = starting_amt - order_cost
    ending_wallet_balance = WalletBalance(walletBalance=ending_amt, positionBalance=order_cost, availableBalance=ending_amt)

    with patch("ordermanager.app.main.api.ContractOrder.place_order", return_value=mock_bybit_api_response), \
        patch("ordermanager.app.main.get_cache_value", side_effect=mock_get_cache_value), \
        patch("ordermanager.app.main.produce_topic_orders_executed", return_value=None), \
        patch("ordermanager.app.main.get_wallet_balance", return_value=starting_wallet_balance), \
        patch("ordermanager.app.main.update_wallet_balance", side_effect=stub_set_wallet_balance) as update_wallet_balance:
            response = await place_order(order_request, jwt_token)            
            assert update_wallet_balance.side_effect.assert_called_with(ending_wallet_balance)
            assert response["retCode"] == 0
            assert response["result"]["orderLinkId"] == mock_bybit_api_response["result"]["orderLinkId"]
                

# Test placing an order with insufficient balance (expect an InsufficientBalanceException)
@pytest.mark.asyncio
async def test_place_order_insufficient_balance(jwt_token):
    headers = {"Authorization": f"Bearer {jwt_token}"}
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

    def mock_get_cache_value(key: str):
        if key.startswith("risk_limits"):
            return mock_risk_limit
        elif key == "wallet_balance":
            return starting_wallet_balance
        else:
            return None
        
    mock_bybit_api_response = {"retCode": 0, "result": {"orderId": "332561", "orderLinkId": "11111"}}

    starting_amt = 3000
    starting_wallet_balance = WalletBalance(walletBalance=starting_amt, positionBalance=0, availableBalance=starting_amt)
    order_cost = calculate_order_cost(order_request, mock_risk_limit.maxLeverage)
    ending_amt = starting_amt - order_cost
    ending_wallet_balance = WalletBalance(walletBalance=ending_amt, positionBalance=order_cost, availableBalance=ending_amt)

    with patch("ordermanager.app.main.api.ContractOrder.place_order", return_value=mock_bybit_api_response), \
        patch("ordermanager.app.main.get_cache_value", side_effect=mock_get_cache_value), \
        patch("ordermanager.app.main.produce_topic_orders_executed", return_value=None), \
        patch("ordermanager.app.main.get_wallet_balance", return_value=starting_wallet_balance), \
        patch("ordermanager.app.main.update_wallet_balance", return_value=None):        
            error_message = await place_order(order_request, jwt_token)
            assert error_message == "error: Insufficient balance: Required 6681.25, available 3000.0"