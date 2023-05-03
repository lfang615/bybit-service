import base64
import httpx
import json
import time
import hmac
import uuid
import hashlib
from orderstateresolver.app.errorcodes import BybitErrorCodes
import logging

class BybitAPIException(Exception):
    pass

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
        
        try:
            if method == "POST":
                response = httpx.post(url, headers=headers, data=payload.json())
                response_data = response.json()
            else:
                response = httpx.get(url + "?" + payload, headers=headers)
                response_data = response.json()
        except httpx.HTTPError as e:
            logging.error(f"Error sending request: {e}")
            raise
        
        if 'retCode' in response_data and response_data['retCode'] != 0:
            error_message = BybitErrorCodes.get_message(response_data['retCode'])
            raise BybitAPIException(f"Error {response_data['retCode']}: {error_message}")

        return response_data
        
    def genSignature(self, payload):
        param_str= str(time_stamp) + self.api_key + self.recv_window + payload
        hash = hmac.new(bytes(self.secret_key, "utf-8"), param_str.encode("utf-8"),hashlib.sha256)
        signature = hash.hexdigest()
        return signature
    
    async def get_order_by_orderLinkId(self, orderLinkId:str):
        try:
            endpoint = "/contract/v3/private/order/list"
            return await self._send_request("GET", endpoint, f'orderLinkId={orderLinkId}')
        except (httpx.HTTPError, BybitAPIException) as e:
            logging.error(f"Error getting order by id: {e}")
            raise

    def get_trading_symbols(self):
        try:        
            endpoint = f"/derivatives/v3/public/tickers"
            return self._send_request("GET", endpoint, "category=linear")
        except (httpx.HTTPError, BybitAPIException) as e:
            logging.error(f"Error getting trading symbols: {e}")
            raise

    def get_risk_limits(self):
        try:        
            endpoint = f"/derivatives/v3/public/risk-limit/list"
            return self._send_request("GET", endpoint)
        except (httpx.HTTPError, BybitAPIException) as e:
            logging.error(f"Error getting risk limits: {e}")
            raise

        