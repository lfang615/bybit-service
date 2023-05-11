from abc import ABC, abstractmethod
from ordermanager.app.services.orderstrategy import OrderStrategy
from ordermanager.app.exceptions import ExchangeAPIException
from httpx import HTTPError
from typing import Type, Dict, Any, Union

class CryptoExchangeAPI(ABC):
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key

    @abstractmethod
    async def _send_request(self, method, endpoint, payload="") -> Union[Dict[str, Any], HTTPError]:
        pass

    @abstractmethod
    def genSignature(self, payload):
        pass

    @abstractmethod
    def get_order_strategy(self) -> Type[OrderStrategy]:
        pass

    class Position(ABC):
        @abstractmethod
        async def set_leverage(self, leverageRequest) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

        @abstractmethod
        async def get_position_p_n_l(self, symbol) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

        @abstractmethod
        async def get_position(self, symbol) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

        @abstractmethod
        async def set_tpsl(self, symbol) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

    class ContractOrder(ABC):
        @abstractmethod
        def set_position_mode(self, order) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

        @abstractmethod
        async def get_order_list(self) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

        @abstractmethod
        async def get_active_orders(self) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

        @abstractmethod
        async def get_new_orders(self) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

        @abstractmethod
        async def get_order_by_id(self, orderId) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

        @abstractmethod
        async def get_order_by_symbol(self, symbol) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

        @abstractmethod
        async def place_order(self, order) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

        @abstractmethod
        async def cancel_order(self, cancelRequest) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

    class Account(ABC):
        @abstractmethod
        def get_balance(self) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

    class MarketData(ABC):
        @abstractmethod
        async def get_trading_symbols(self) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass

        @abstractmethod
        async def get_risk_limits(self, symbol) -> Union[Dict[str, Any], HTTPError, ExchangeAPIException]:
            pass
