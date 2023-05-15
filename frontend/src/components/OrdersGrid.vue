<template>
  <div class="table-responsive">
    <div class="d-flex justify-content-between">
      <div class="btn-group" role="group">
        <input @click="displayType = 'positions'" type="radio" class="btn-check" name="btnradio" id="btnradio1" autocomplete="off" checked>
        <label class="btn btn-outline-primary" for="btnradio1">Positions</label>
        <input @click="displayType = 'currentOrders'" type="radio" class="btn-check" name="btnradio" id="btnradio2" autocomplete="off">
        <label class="btn btn-outline-primary" for="btnradio2">Current Orders</label>
      </div>
      <button @click="refreshGrid" class="btn btn-outline-secondary">Refrersh Grid</button>
  </div>

  <table class="table" v-show="displayType == 'positions'">
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Side</th>
          <th>Qty</th>
          <th>AEP</th>
          <th>Status</th>
          <th>StopOrderType</th>
          <th>OpenDate</th>          
        </tr>
      </thead>
      <tbody>
        <tr v-for="position in positions" :key="position.symbol">
          <td>{{ position.symbol }}</td>
          <td>{{ position.side }}</td>
          <td>{{ position.qty }}</td>
          <td>{{ position.price }}</td>                    
          <td>{{ position.orderStatus }}</td>
          <td>{{ position.stopLoss }}</td>
          <td>{{ position.takeProfit }}</td>
          <td>{{ position.openDate }}</td>
        </tr>
      </tbody>
    </table>
    <table class="table" v-show="displayType == 'currentOrders'">
      <thead>
        <tr>
          <th>Order ID</th>
          <th>Contract</th>
          <th>Order Type</th>
          <th>Side</th>
          <th>Qty</th>
          <th>Price</th>
          <th>Status</th>
          <th>StopOrderType</th>          
        </tr>
      </thead>
      <tbody>
        <tr v-for="order in orders" :key="order.orderId">
          <td>{{ order.orderId }}</td>
          <td>{{ order.symbol }}</td>
          <td>{{ order.orderType }}</td>
          <td>{{ order.side }}</td>
          <td>{{ order.qty }}</td>
          <td>{{ order.price }}</td>                    
          <td>{{ order.orderStatus }}</td>
          <td>{{ order.stopOrderType }}</td>
          <td>
            <button class="btn btn-sm btn-primary" @click.stop="editOrder(order)">Edit</button>
          </td>
          <td>
            <button class="btn btn-sm btn-danger" @click.stop="cancelOrder(order)">Cancel</button>
          </td> 
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import axios from "axios";

export default {
  data() {
    return {
      positions: [],
      socketOrders: null,
      socketPositions: null,
      orders: [],
      displayType: 'positions',
      showEditOrderModal: false,
      selectedOrder: null,
    };
  },
  created() {
    this.connect();
    this.fetchOrders();
  },
  methods: {
    async refreshOrders() {
      try {
        const response = await axios.get('http://localhost:5000/refresh_orders');
        this.orders = response.data;
      } catch (error) {
        console.error('Failed to fetch orders:', error);
      }
    },

    editOrder(order) {
      this.selectedOrder = order;
      this.showEditOrderModal = true;
    },

    cancelOrder(order){
      try{
        const response = axios.post('http://localhost:5000/cancel_order', {
          orderId: order.orderId,
        });
        if(response.data['retCode'] === 0){
          this.showMessageModal('Order Cancel Successful', `Order ${order.orderId} has been cancelled.`);
        } else {
          this.showMessageModal('Order Cancel Failed', `Order ${order.orderId} could not be cancelled. Error: ${response.data['retMsg']}`);
        }
      } catch(error){
        console.error('Failed to cancel order:', error);
      }
    },

    async fetchOrders(){
      try {
        const response = await axios.get('http://localhost:5000/orders');
        this.orders = response.data;
      } catch (error) {
        console.error('Failed to fetch orders:', error);
      }
    },
    async fetchPositions(){
      try{
        const response = await axios.get('http://localhost:5000/positions');
        this.positions = response.data;
      } catch(error){
        console.error('Failed to fetch positions:', error);
      }
    },
    connect() {
      this.socketOrders = new WebSocket(`ws://${process.env.VUE_APP_API_BASE_URL}/ws/orders`);
      this.socketOrders.addEventListener('open', this.onOpen);
      this.socketOrders.addEventListener('error', this.onError);
      this.socketOrders.addEventListener('close', this.onClose);
      this.socketOrders.addEventListener('message', this.onMessage);

      this.socketPositions = new WebSocket(`ws://${process.env.VUE_APP_API_BASE_URL}/ws/positions`);
      this.socketPositions.addEventListener('open', this.onOpen);
      this.socketPositions.addEventListener('error', this.onError);
      this.socketPositions.addEventListener('close', this.onClose);
      this.socketPositions.addEventListener('message', this.onMessage);
    },
    onOpen(event) {
      console.log('WebSocket connected:', event);
    },
    onMessage(event) {
      const updatedOrder = JSON.parse(event.data);
      // Update the order in the orders array based on the received data
      const orderIndex = this.orders.findIndex(order => order.orderId === updatedOrder.orderId);
      if (orderIndex !== -1) {
        this.orders.splice(orderIndex, 1, updatedOrder);
      }
    },
    onError(event) {
      console.error('WebSocket error:', event);
    },
    onClose(event) {
      console.log('WebSocket closed:', event);
    },
    showMessageModal(messageModalTitle, messageModalMessage){
      this.$emit('show-message-modal', {'messageModalTitle': messageModalTitle, 'messageModalMessage': messageModalMessage});
    }
  },
};
</script>
