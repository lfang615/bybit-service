<template>
  <div class="table-responsive">
    <h2>Open and Pending Orders</h2>
    <button @click="fetchOrders">Refresh Orders</button>
    <button @click="displayType = 'positions'">Positions</button>
    <button @click="displayType = 'currentOrders'">Current Orders</button>
    <table class="table" v-if="displayedOrders.length">
      <thead>
        <tr>
          <th>Order ID</th>
          <th>Trading Pair</th>
          <th>Quantity</th>
          <th>Price</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="order in displayedOrders" :key="order.id">
          <td>{{ order.id }}</td>
          <td>{{ order.trading_pair }}</td>
          <td>{{ order.quantity }}</td>
          <td>{{ order.price }}</td>
          <td>{{ order.status }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else>No orders found.</p>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      socket: null,
      orders: [],
      displayType: 'positions',
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
    async fetchOrders() {
      try {
        const response = await axios.get('http://localhost:8000/orders');
        this.orders = response.data;
      } catch (error) {
        console.error('Failed to fetch orders:', error);
      }
    },
    connect() {
      this.socket = new WebSocket('ws://localhost:8000/ws');
      this.socket.addEventListener('message', this.onMessage);
    },
    onMessage(event) {
      const updatedOrder = JSON.parse(event.data);
      // Update the order in the orders array based on the received data
      const orderIndex = this.orders.findIndex(order => order.id === updatedOrder.id);
      if (orderIndex !== -1) {
        this.orders.splice(orderIndex, 1, updatedOrder);
      }
    },
  },
};
</script>
