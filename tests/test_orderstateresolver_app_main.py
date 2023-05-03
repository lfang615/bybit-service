from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from orderstateresolver.app.models.order import Order, OrderSide
from orderstateresolver.app.models.position import Position
from orderstateresolver.app.main import update_positions_cache
import json


def mock_redis_client(position: dict):
    return
    
def create_bybit_order_mock():
    bybit_order_mock = Order(
        symbol="BTCUSDT",
        side="Buy",
        orderType="Limit",
        price="30000",
        qty="1",
        orderLinkId="123456",
        orderId="123",
        timeInForce="GoodTillCancel",
        cumExecQty="1",
        orderStatus=None,
        positionIdx=None,
        triggerBy=None,
        stopOrderType=None,
        takeProfit=None,
        stopLoss=None,
        tpTriggerBy=None,
        slTriggerBy=None,
        triggerPrice=None,
        cancelType=None,
        reduceOnly=False,
        leavesQty=None,
        leavesValue=None,       
        cumExecValue=None,
        cumExecFee=None,
        lastPriceOncreated=None,
        rejectReason=None,
        triggerDirection=None,
        closeOnTrigger=None,
        iv=None
        )
    return bybit_order_mock

# Parametrize the fixture to run tests for both "Buy" (Long) and "Sell" Short positions
@pytest.fixture(scope="function")
def order_side(request):
    return request.param

@pytest.mark.parametrize("order_side", [OrderSide.BUY.value, OrderSide.SELL.value], indirect=True)
@pytest.mark.asyncio
async def test_update_positions_cache_new_position(order_side):
    bybit_order_mock = create_bybit_order_mock()
    bybit_order_mock.cumExecQty = "2"
    bybit_order_mock.price = "30000"
    bybit_order_mock.side = order_side

    with patch("orderstateresolver.app.main.set_cache_value", new_callable=AsyncMock, return_value=None) as redis_client_mock, \
        patch("orderstateresolver.app.main.get_cache_value", new_callable=AsyncMock, return_value=None) as redis_get_mock:
        position = await update_positions_cache(bybit_order_mock)

        # Check if the new position has the correct values
        assert position.symbol == bybit_order_mock.symbol
        assert position.side == bybit_order_mock.side
        assert position.qty == bybit_order_mock.cumExecQty
        assert position.aep == bybit_order_mock.price
        assert position.linkedOrders == [bybit_order_mock]

        # Check if the position was stored in the cache
        redis_client_mock.assert_called_once_with(
            f"positions:{bybit_order_mock.symbol}:{order_side}", position
        )

# Parametrize the fixture to run tests for both "Buy" (Long) and "Sell" Short positions
@pytest.mark.parametrize("order_side", [OrderSide.BUY.value, OrderSide.SELL.value], indirect=True)
@pytest.mark.asyncio
async def test_update_positions_cache_existing_position(order_side):
    existing_position = Position(
        symbol="BTCUSDT",
        side=order_side,
        openDate="01/01/2023 00:00",
        qty=1,
        aep=20000,
        linkedOrders=[
            Order(
                symbol="BTCUSDT",
                side=order_side,
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

   
    redis_client_mock = mock_redis_client(existing_position)
    bybit_order_mock = create_bybit_order_mock()
    bybit_order_mock.side=order_side
    bybit_order_mock.orderLinkId = "RandomId"
    bybit_order_mock.cumExecQty = 2

    with patch("orderstateresolver.app.main.get_cache_value", new_callable=AsyncMock, return_value=existing_position.json()), \
        patch("orderstateresolver.app.main.set_cache_value", new_callable=AsyncMock, return_value=None) as redis_client_mock:
        position = await update_positions_cache(bybit_order_mock)

        # Check if the updated position has the correct values
        assert position.symbol == bybit_order_mock.symbol
        assert position.side == bybit_order_mock.side
        assert position.qty == existing_position.qty + bybit_order_mock.cumExecQty
        assert position.aep == (existing_position.aep + bybit_order_mock.price) / 2
        assert position.linkedOrders == existing_position.linkedOrders + [bybit_order_mock]

        # Check if the position was stored in the cache
        redis_client_mock.assert_called_once_with(
            f"positions:{existing_position.symbol}:{order_side}", position
        )

@pytest.mark.parametrize("order_side", [OrderSide.BUY.value, OrderSide.SELL.value], indirect=True)
@pytest.mark.asyncio
async def test_update_positions_cache_reduce_only(order_side):
    existing_position = Position(
        symbol="BTCUSDT",
        side=order_side,
        openDate="01/01/2023 00:00",
        qty=3,
        aep=35000,
        linkedOrders=[
            Order(
                symbol="BTCUSDT",
                side=order_side,
                orderType="Limit",
                price="35000",
                qty="3",
                orderLinkId="123456",
                orderStatus="Filled",
                orderId="123",
                timeInForce="GoodTillCancel",
                reduceOnly=False,
                cumExecQty="3"
            )
        ]
    )

    redis_client_mock = mock_redis_client(existing_position)
    bybit_order_mock = create_bybit_order_mock()
    bybit_order_mock.side = OrderSide.SELL.value if order_side == OrderSide.BUY.value else OrderSide.BUY.value
    bybit_order_mock.reduceOnly = True
    bybit_order_mock.orderLinkId = "RandomId"
    bybit_order_mock.cumExecQty = 1

    with patch("orderstateresolver.app.main.get_cache_value", new_callable=AsyncMock, return_value=existing_position.json()), \
        patch("orderstateresolver.app.main.set_cache_value", new_callable=AsyncMock, return_value=None) as redis_client_mock:
        position = await update_positions_cache(bybit_order_mock)

        # Check if the updated position has the correct values
        assert position.symbol == bybit_order_mock.symbol
        assert position.qty == existing_position.qty - bybit_order_mock.cumExecQty
        assert position.aep == existing_position.aep
        assert position.linkedOrders == existing_position.linkedOrders + [bybit_order_mock]

        # Check if the position was stored in the cache
        redis_client_mock.assert_called_once_with(
            f"positions:{existing_position.symbol}:{existing_position.side}", position
        )


# Check if position key is deleted from the cache when the position is closed based on matching closing orders
@pytest.mark.parametrize("order_side", [OrderSide.BUY.value, OrderSide.SELL.value], indirect=True)
@pytest.mark.asyncio
async def test_update_positions_cache_close_position(order_side):
    existing_position = Position(
        symbol="BTCUSDT",
        side=order_side,
        openDate="01/01/2023 00:00",
        qty=2,
        aep=32000,
        linkedOrders=[
            Order(
                symbol="BTCUSDT",
                side=order_side,
                orderType="Limit",
                price="32000",
                qty="2",
                cumExecQty="2",
                orderLinkId="123456",
                orderStatus="Filled",
                orderId="123",
                timeInForce="GoodTillCancel",
                reduceOnly=False
            )
        ]
    )
        
    redis_client_mock = mock_redis_client(existing_position)
    bybit_order_mock = create_bybit_order_mock()

    bybit_order_mock.orderLinkId = "order-to-close-position"
    bybit_order_mock.orderId = "RandomId"
    bybit_order_mock.side = OrderSide.SELL.value if order_side == OrderSide.BUY.value else OrderSide.BUY.value
    bybit_order_mock.reduceOnly = True
    bybit_order_mock.cumExecQty = 2
    bybit_order_mock.orderStatus = "Filled"
    
    with patch("orderstateresolver.app.main.get_cache_value", new_callable=AsyncMock, return_value=existing_position.json()), \
        patch("orderstateresolver.app.main.delete_cache_value", new_callable=AsyncMock, return_value=None) as redis_client_mock:
        position = await update_positions_cache(bybit_order_mock)

        # Check if the updated position has the correct values
        assert position.qty == 0
        assert position.linkedOrders == existing_position.linkedOrders + [bybit_order_mock]
        assert position.closeDate is not None

        # Check if the position key/value was deleted from the cache
        redis_client_mock.assert_called_once_with(
            f"positions:{existing_position.symbol}:{existing_position.side}"
        )


# Check that contracts of the same symbol for opposite sides are maintained individually in the cache
# Opens a short position for BTCUSDT while a long position for BTCUSDT exists and checks if the cache is updated correctly
# Check if the correct cache key is used to save position values when both LONG and SHORT positions exist for the same symbol
@pytest.mark.parametrize("order_side", [OrderSide.BUY.value, OrderSide.SELL.value], indirect=True)
@pytest.mark.asyncio
async def test_update_positions_cache_opposite_side_without_closing(order_side):
    existing_position = Position(
    symbol="BTCUSDT",
    side=order_side,
    openDate="01/01/2023 00:00",
    qty=2,
    aep=32000,
    linkedOrders=[
        Order(
            symbol="BTCUSDT",
            side=order_side,
            orderType="Limit",
            price="32000",
            qty="2",
            orderStatus="PartiallyFilled",
            cumExecQty="2",
            orderLinkId="123456",
            orderId="123",
            timeInForce="GoodTillCancel",
            reduceOnly=False
            )
        ]
    )

    redis_client_mock = mock_redis_client(existing_position)
    bybit_order_mock = create_bybit_order_mock()
    bybit_order_mock.orderStatus = "Filled"
    bybit_order_mock.side = OrderSide.SELL.value if order_side == OrderSide.BUY.value else OrderSide.BUY.value
    bybit_order_mock.qty = 5
    bybit_order_mock.cumExecQty = 5
    bybit_order_mock.orderLinkId = "RandomId"
    
    with patch("orderstateresolver.app.main.get_cache_value", new_callable=AsyncMock, return_value=existing_position.json()) as redis_get_key, \
        patch("orderstateresolver.app.main.set_cache_value", new_callable=AsyncMock, return_value=None) as redis_client_mock:
        position = await update_positions_cache(bybit_order_mock)

        # position.qty should be the sum of cumExecQty of all linked orders
        assert position.qty == existing_position.linkedOrders[0].cumExecQty + bybit_order_mock.cumExecQty
        assert position.aep == (existing_position.linkedOrders[0].price + bybit_order_mock.price) / 2
        assert position.linkedOrders == existing_position.linkedOrders + [bybit_order_mock]

        # Check if the correct key is used when both LONG and SHORT positions are open for the same symbol
        redis_get_key.assert_called_once_with(f"positions:{bybit_order_mock.symbol}:{bybit_order_mock.side}")
        
        # Check if the position was stored in the cache
        redis_client_mock.assert_called_once_with(
            f"positions:{bybit_order_mock.symbol}:{bybit_order_mock.side}", position
        )