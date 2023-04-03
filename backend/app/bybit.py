import base64
import requests
import httpx
import datetime
import time
import hmac
import uuid
import hashlib
from Crypto.Hash import SHA256  # install pycryptodome libaray
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA

class BybitAPI:
    def __init__(self, api_key, secret_key):
        self.base_url = "https://api.bybit.com"
        self.api_key = api_key
        self.secret_key = secret_key
        self.recv_window = str(5000)
        
    def _send_request(self, method, endpoint, params=""):
        global time_stamp
        time_stamp=str(int(time.time() * 10 ** 3))
        url = f"{self.base_url}{endpoint}"
        signature = self.genSignature(params)
        
        headers = {
            "api-key": self.api_key,
            "api-secret": self.secret_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": str(int(datetime.datetime.now().timestamp() * 1000)),
            "X-BAPI-RECV-WINDOW": self.recv_window,
            # "cdn-request-id": "cdn_request_id"
            }
        response = requests.request(method, url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def genSignature(self, payload):
        param_str= str(time_stamp) + self.api_key + self.recv_window + payload
        hash = hmac.new(bytes(self.secret_key, "utf-8"), param_str.encode("utf-8"),hashlib.sha256)
        signature = hash.hexdigest()
        return signature
    
    class Position:
        def __init__(self, api):
            self.api = api
        
        def get_all_positions(self):
            endpoint = "/contract/v3/private/position/list"
            return self.api._send_request("GET", endpoint)
        
        def get_position(self, symbol):
            endpoint = f"/v5/private/position/list?symbol={symbol}"
            return self.api._send_request("GET", endpoint)

        # Add more methods as needed...

    class Trade:
        def __init__(self, api):
            self.api = api
        
        def get_order(self, order_id):
            endpoint = f"/v2/private/order?order_id={order_id}"
            return self.api._send_request("GET", endpoint)

        # Add more methods as needed...

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