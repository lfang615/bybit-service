

class Order:
    def __init__(self, orderType, qty, takeProfit=None, stopLoss=None, triggerDirection=None, triggerPrice=None):
        self.orderType = orderType
        self.qty = qty
        self.takeProfit = takeProfit
        self.stopLoss = stopLoss
        self.triggerDirection = triggerDirection
        self.triggerPrice = triggerPrice

    
    def set_order_id(self, order_id):
        self.order_id = order_id

    