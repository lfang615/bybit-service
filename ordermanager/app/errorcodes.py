from enum import Enum

class BybitErrorCodes(Enum):
    SERVER_TIMEOUT = (10000, "Server Timeout")
    PARAMS_ERROR = (10001, "params error")
    INVALID_REQUEST = (10002, "Invalid request, please check your timestamp and recv_window param")
    INVALID_API_KEY = (10003, "Invalid api_key")
    ERROR_SIGN = (10004, "Error sign")
    PERMISSION_DENIED = (10005, "Permission denied")
    TOO_MANY_VISITS = (10006, "Too many visits")
    USER_BANNED = (10008, "User had been banned. Please check your account mode")
    IP_BANNED = (10009, "IP had been banned")
    UNMATCHED_IP = (10010, "unmatched IP")
    DUPLICATE_REQUEST = (10014, "Request is duplicate")
    SERVER_ERROR = (10016, "Server Error")
    OUT_OF_FREQUENCY_LIMIT = (10018, "Out of frequency limit of IP")
    TRADING_BANNED = (10027, "Trading is banned")
    ORDER_NOT_EXIST = (140001, "Order does not exist")
    INVALID_ORDER_PRICE = (140003, "Order is out of permissible range")
    INSUFFICIENT_WALLET = (140004, "Insufficient wallet balance")
    POSITION_STATUS = (140005, "position status")
    INVALID_MARGIN = (140006, "cannot afford estimated position margin")
    AVAILABLE_BALANCE = (140007, "insufficient available balance")
    ORDER_FINISHED = (140008, "Order has been finished or cancelled")
    STOP_ORDER_MAX = (140009, "The number of stop orders exceeds maximum limit allowed")
    ORDER_CANCELLED = (140010, "Order already cancelled")
    IMMEDIATE_LIQUIDATION = (140011, "Any adjustments made will trigger immediate liquidation")
    AVAILABLE_BALANCE_INSUFFICIENT = (140012, "Insufficient available balance")
    RISK_LIMIT = (140013, "Due to risk limit, cannot set leverage")
    BALANCE_NOT_ENOUGH_MARGIN = (140014, "Available balance not enough to add margin")
    POSITION_IS_CROSS_MARGIN = (140015, "Position is in cross margin")
    CONTRACT_QTY_EXCEEDS_LIMIT = (140016, "Requested quantity of contracts exceeds risk limit, please adjust your risk limit level before trying again")
    REDUCE_ONLY_NOT_SATISFIED = (140017, "Reduce-only rule not satisfied")
    USER_ID_ILLEGAL = (140018, "User ID illegal")
    ORDER_ID_ILLEGAL = (140019, "Order ID illegal")
    QUANTITY_LIMITED = (140020, "qty has been limited, cannot modify the order to add qty")
    REDUCTION_SUPPORT_ONLY = (140023, "This contract only supports position reduction operation, please contact customer service for details")
    DUPLICATE_ORDER_ID = (140030, "Duplicate order ID")
    ILLEGAL_ORDER = (140032, "Illegal order")
    CANT_SET_MARGIN = (140033, "Margin cannot be set without open position")
    MAINTAIN_MARGIN_HIGH = (140039, "Maintain margin rate is too high, which may trigger liquidation")
    ORDER_TRIGGER_LIQUIDATION = (140040, "Order will trigger forced liquidation, please resubmit the order")
    LEVERAGE_NOT_MODIFIED = (140043, "Set leverage not modified")
    INSUFFICIENT_AVAILABLE_MARGIN = (140044, "Insufficient available margin")
    INVALID_TPSL = (140058, "Insufficient number of remaining position size to set take profit and stop loss")
    FULL_TPSL = (140060, "Under full TP/SL mode, it is not allowed to modify TP/SL")
    PARTIAL_TPSL = (140061, "Under partial TP/SL mode, TP/SL set more than 20")
    QTY_REPLACE_INVALID = (140064, "The number of contracts modified cannot be less than or equal to the filled quantity")
    TRADING_NOT_ALLOWED = (140066, "No trading is allowed at the current time")
    
    # Add the remaining error codes here

    def __init__(self, code, message):
        self.code = code
        self.message = message

    @classmethod
    def get_message(cls, code):
        for error_code in cls:
            if error_code.code == code:
                return error_code.message
        return "Unknown error code"