import httpx
import time
import hmac
import hashlib
from ordermanager.app.models.order import Order, OrderRequest, LeverageRequest, CancelRequest
from ordermanager.app.services.abstractexchange import CryptoExchangeAPI as AbstractExchange
from ordermanager.app.errorcodes import BybitErrorCodes 
import logging
from ordermanager.app.exceptions import ExchangeAPIException
from ordermanager.app.services.orderstrategy import OrderStrategy
from ordermanager.app.services.bybitorderstrategy import BybitOrderStrategy
from typing import Type


class BybitAPI(AbstractExchange):
    def __init__(self, api_key, secret_key):
        super().__init__(api_key, secret_key)
        self.base_url = "https://api.bybit.com"
        self.recv_window = str(5000)
        
    async def _send_request(self, method, endpoint, payload=""):
        global time_stamp
        time_stamp=str(int(time.time() * 10 ** 3))
        url = f"{self.base_url}{endpoint}"

        if method == "POST":
            signature = self.genSignature(payload.json())
        else:
            signature = self.genSignature(payload)
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "X-BAPI-SIGN": signature,
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": time_stamp,
            "X-BAPI-RECV-WINDOW": self.recv_window,
            # "cdn-request-id": "cdn_request_id"
            }
        
        try:
            async with httpx.AsyncClient() as client:
                if method == "POST":
                    response = await client.post(url, headers=headers, data=payload.json())
                    response_data = response.json()
                else:
                    response = await client.get(url + "?" + payload, headers=headers)
                    response_data = response.json()
        except httpx.HTTPError as e:
            logging.error(f"Error sending request: {e}")
            raise
        
        if 'retCode' in response_data and response_data['retCode'] != 0:
                error_message = BybitErrorCodes.get_message(response_data['retCode'])
                raise ExchangeAPIException(f"Error {response_data['retCode']}: {error_message}")

        return response_data
        
    def genSignature(self, payload):
        param_str= str(time_stamp) + self.api_key + self.recv_window + payload
        hash = hmac.new(bytes(self.secret_key, "utf-8"), param_str.encode("utf-8"),hashlib.sha256)
        signature = hash.hexdigest()
        return signature
    
    def get_order_strategy(self) -> Type[OrderStrategy]:
        return BybitOrderStrategy
    
    class Position:
        def __init__(self, api):
            self.api = api
        
        async def set_leverage(self, leverageRequest:LeverageRequest):
            try:
                endpoint = "/contract/v3/private/position/set-leverage"
                return await self.api._send_request("POST", endpoint, leverageRequest)
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error setting leverage: {e}")
                raise
        
        async def get_position_p_n_l(self, symbol:str):
            try:
                endpoint = f"/contract/v3/private/position/closed-pnl"
                return await self.api._send_request("GET", endpoint, f'symbol={symbol}')
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error getting position PnL: {e}")
                raise
        
        async def get_position(self, symbol:str):
            try:
                endpoint = f"/contract/v3/private/position/list"
                return await self.api._send_request("GET", endpoint, f'symbol={symbol}')
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error getting position status: {e}")
                raise

        async def set_tpsl(self, symbol:str):
            try:
                endpoint = f"/contract/v3/private/position/trading-stop"
                return await self.api._send_request("POST", endpoint, f'symbol={symbol}')
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error setting TP/SL: {e}")
                raise

    class ContractOrder:
        def __init__(self, api):
            self.api = api

        def set_position_mode(self, order:OrderRequest):
            match order.side:
                case 'Buy':
                    order.positionIdx = 1
                case 'Sell':
                    order.positionIdx = 2
        

        async def get_order_list(self):
            try:
                endpoint = "/contract/v3/private/order/list"
                return await self.api._send_request("GET", endpoint, f'category=linear&orderFilter=order')
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error getting order list: {e}")

        async def get_active_orders(self):
            try:
                endpoint = "/contract/v3/private/order/list"
                return await self.api._send_request("GET", endpoint, f'symbol=APEUSDT')
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error getting active orders: {e}")
                raise

        async def get_new_orders(self):
            try:
                endpoint = "/contract/v3/private/order/list"
                return await self.api._send_request("GET", endpoint, f'orderStatus=New')
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error getting new orders: {e}")
                raise

        async def get_order_by_id(self, orderId:str):
            try:
                endpoint = "/contract/v3/private/order/list"
                return await self.api._send_request("GET", endpoint, f'orderId={orderId}')
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error getting order by id: {e}")
                raise

        async def get_order_by_symbol(self, symbol:str):
            try:
                endpoint = "/contract/v3/private/order/list"
                return await self.api._send_request("GET", endpoint, f'symbol={symbol}')
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error getting order by symbol: {e}")
                raise

        async def place_order(self, order:OrderRequest):
            try: 
                endpoint = "/contract/v3/private/order/create"
                self.set_position_mode(order)
                return await self.api._send_request("POST", endpoint, order)
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error placing order: {e}")
                raise
        
        async def cancel_order(self, cancelRequest:CancelRequest):
            try:
                endpoint = "/contract/v3/private/order/cancel"
                return await self.api._send_request("POST", endpoint, cancelRequest)
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error cancelling order: {e}")
                raise
            
    class Account:
        def __init__(self, api):
            self.api = api
        
        def get_balance(self):
            try:    
                endpoint = "/v2/private/wallet/balance"
                return self.api._send_request("GET", endpoint)
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error getting balance: {e}")
                raise
        
    class MarketData:
        def __init__(self, api):
            self.api = api

        async def get_trading_symbols(self):
            try:        
                endpoint = f"/derivatives/v3/public/tickers"
                return self.api._send_request("GET", endpoint, "category=linear")
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error getting trading symbols: {e}")
                raise

        async def get_risk_limits(self, symbol:str):
            try:        
                endpoint = f"/derivatives/v3/public/risk-limit/list"
                return await self.api._send_request("GET", endpoint, f'symbol={symbol}')
            except (httpx.HTTPError, ExchangeAPIException) as e:
                logging.error(f"Error getting risk limit: {e}")
                raise