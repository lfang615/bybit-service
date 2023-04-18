<template>
  <div class="table-responsive">
    <div class="d-flex justify-content-between">
      <div class="btn-group" role="group">
        <input @click="displayType = 'positions'" type="radio" class="btn-check" name="btnradio" id="btnradio1" autocomplete="off" checked>
        <label class="btn btn-outline-primary" for="btnradio1">Positions</label>
        <input @click="displayType = 'currentOrders'" type="radio" class="btn-check" name="btnradio" id="btnradio2" autocomplete="off">
        <label class="btn btn-outline-primary" for="btnradio2">Current Orders</label>
      </div>
      <button @click="refreshOrders" class="btn btn-outline-secondary">Refrersh Orders</button>
  </div>
    <table class="table" v-if="displayedOrders.length">
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
        <tr v-for="order in displayedOrders" :key="order.orderId">
          <td>{{ order.orderId }}</td>
          <td>{{ order.symbol }}</td>
          <td>{{ order.orderType }}</td>
          <td>{{ order.side }}</td>
          <td>{{ order.qty }}</td>
          <td>{{ order.price }}</td>                    
          <td>{{ order.orderStatus }}</td>
          <td>{{ order.stopOrderType }}</td>
          <td v-if="displayType === 'currentOrders'">
            <button class="btn btn-sm btn-primary" @click.stop="editOrder(order)">Edit</button>
          </td>
          <td v-if="displayType === 'currentOrders'">
            <button class="btn btn-sm btn-danger" @click.stop="cancelOrder(order)">Cancel</button>
          </td> <td v-if="displayType === 'currentOrders'">
            <button class="btn btn-sm btn-primary" @click.stop="editOrder(order)">Edit</button>
          </td>
          <td v-if="displayType === 'currentOrders'">
            <button class="btn btn-sm btn-danger" @click.stop="cancelOrder(order)">Cancel</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else>No orders found.</p>
  </div>
</template>

<script>
import axios from "axios";

export default {
  data() {
    return {
      socket: null,
      orders: [],
      displayType: 'positions',
      showEditOrderModal: false,
      selectedOrder: null,
    };
  },
  computed: {
    positions() {
      return this.orders.filter(order => order.orderStatus === "Filled" || order.orderStatus === "PartiallyFilled");
    },
    currentOrders() {
      return this.orders.filter(order => order.orderStatus === "PartiallyFilled" || order.reduceOnly === true);
    },
    displayedOrders() {
      return this.displayType === 'positions' ? this.positions : this.currentOrders;
    },
  },
  created() {
    this.connect();
    this.fetchOrders();
  },
  methods: {
    async refreshOrders() {
      try {
        const response = await axios.get('http://localhost:8000/refresh_orders');
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
        const response = axios.post('http://localhost:8000/cancel_order', {
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
        const response = await axios.get('http://localhost:8000/open_positions_orders');
        this.orders = response.data;
      } catch (error) {
        console.error('Failed to fetch orders:', error);
      }
    },
    connect() {
      this.socket = new WebSocket('ws://localhost:8000/ws/order_updates');
      this.socket.addEventListener('open', this.onOpen);
      this.socket.addEventListener('error', this.onError);
      this.socket.addEventListener('close', this.onClose);
      this.socket.addEventListener('message', this.onMessage);
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
