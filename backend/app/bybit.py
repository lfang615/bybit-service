import base64
import requests
import httpx
import datetime
import json
import time
import hmac
import uuid
import hashlib
from backend.app.models.request.order import Order, OrderRequest, CancelRequest

class BybitAPI:
    def __init__(self, api_key, secret_key):
        self.base_url = "https://api.bybit.com"
        self.api_key = api_key
        self.secret_key = secret_key
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
        
        if method == "POST":
            response = httpx.post(url, headers=headers, data=payload.json())
            return response.json()
        else:
            response = httpx.get(url + "?" + payload, headers=headers)
            return response.json()
        
    def genSignature(self, payload):
        param_str= str(time_stamp) + self.api_key + self.recv_window + payload
        hash = hmac.new(bytes(self.secret_key, "utf-8"), param_str.encode("utf-8"),hashlib.sha256)
        signature = hash.hexdigest()
        return signature
    
    class Position:
        def __init__(self, api):
            self.api = api
        
        async def get_all_positions(self):
            endpoint = "/contract/v3/private/position/list"
            return await self.api._send_request("GET", endpoint)
        
        async def get_position_p_n_l(self, symbol:str):
            endpoint = f"/contract/v3/private/position/closed-pnl"
            return await self.api._send_request("GET", endpoint, f'symbol={symbol}')
        
        async def get_position_status(self, symbol:str):
            endpoint = f"/contract/v3/private/position/list"
            return await self.api._send_request("GET", endpoint, f'symbol={symbol}')

    class ContractOrder:
        def __init__(self, api):
            self.api = api

        def set_position_mode(self, order:OrderRequest):
            match order.side:
                case 'Buy':
                    order.positionIdx = 1
                case 'Sell':
                    order.positionIdx = 2
        
        async def get_open_orders(self, orderId:str):
            endpoint = "/contract/v3/private/order/unfilled-orders"
            return await self.api._send_request("GET", endpoint, f'orderId={orderId}')
        
        async def get_order_list(self):
            endpoint = "/contract/v3/private/order/list"
            return await self.api._send_request("GET", endpoint, f'category=linear&orderFilter=order')
        
        async def get_active_orders(self):
            endpoint = "/contract/v3/private/order/list"
            return await self.api._send_request("GET", endpoint, f'symbol=APEUSDT')
        
        async def get_new_orders(self):
            endpoint = "/contract/v3/private/order/list"
            return await self.api._send_request("GET", endpoint, f'orderStatus=New')

        async def get_order_by_id(self, orderId:str):
            endpoint = "/contract/v3/private/order/list"
            return await self.api._send_request("GET", endpoint, f'orderId={orderId}')

        async def place_order(self, order:OrderRequest):
            endpoint = "/contract/v3/private/order/create"
            self.set_position_mode(order)
            return await self.api._send_request("POST", endpoint, order)
        
        # async def cancel_order(self, order_id:str):
        #     endpoint = "/contract/v3/private/order/cancel"
        #     cancelRequest = CancelRequests(order_id)
        #     return await self.api._send_request("POST", endpoint, cancelRequest)
            
    class Account:
        def __init__(self, api):
            self.api = api
        
        def get_balance(self):
            endpoint = "/v2/private/wallet/balance"
            return self.api._send_request("GET", endpoint)
        
    class MarketData:
        def __init__(self, api):
            self.api = api

        def get_trading_symbols(self):
            endpoint = f"/derivatives/v3/public/tickers?category=linear"
            return self.api._send_request("GET", endpoint)

        # Add more methods as needed...