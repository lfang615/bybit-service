<!-- frontend/src/components/BybitOrderForm.vue -->
<template>
  <div class="container mt-5">
    <div class="row">
      <div class="col">
        <ul class="nav nav-tabs">
          <li class="nav-item">
            <a class="nav-link" :class="{ active: side == 'open'}" @click="side = 'open'" href="#">Open</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" :class="{ active: side == 'close'}" @click="side = 'close'" href="#">Close</a>
          </li>
        </ul>
      </div>
    </div>

    <div class="row mt-2">
      <div class="col">
        <div class="btn-group mt-3" role="group" aria-label="Basic outlined example">
          <button type="button" class="btn btn-outline-primary"
           :class="{ active: order_type == 'limit'}"
           @click="order_type = 'limit'">Limit</button>
          <button type="button" class="btn btn-outline-primary" 
          :class="{ active: order_type == 'market'}"
          @click="order_type = 'market'">Market</button>
          <button type="button" class="btn btn-outline-primary" 
            :class="{ active: order_type == 'conditional'}"
            @click="order_type = 'conditional'">Conditional</button>
        </div>    
      </div>
    </div>

    <div class="row mt-4">
      <div class="col">
        <form @submit.prevent="submitOrder">
          <div>
            <label for="symbol" class="form-label">Symbol:</label>
            <input type="text" id="symbol" class="form-control" :value="selectedSymbol" disabled required />
          </div>
          <div>
            <label for="qty" class="form-label">Quantity:</label>
            <input type="number" id="qty" class="form-control" v-model="qty" required />
          </div>
          <div>
            <label for="price" class="form-label">Price:</label>
            <input type="number" id="price" class="form-control" v-model="price" required />
          </div>
         
          <div>
            <label for="time_in_force" class="form-label">Time in Force:</label>
            <select id="time_in_force" class="form-select" v-model="time_in_force" required>
              <option value="GoodTillCancel">Good Till Cancel</option>
              <option value="ImmediateOrCancel">Immediate or Cancel</option>
              <option value="FillOrKill">Fill or Kill</option>
            </select>
          </div>
          <div class="form-check mt-3">
            <input clqawss="form-check-input" type="checkbox" id="chk-long-tpsl" v-model="tpsl">
            <label class="form-check-label" for="chk-long-tpsl">Set TP/SL</label>
          </div>
          <div v-show="tpsl">
            <div>
              <label for="take_profit" class="form-label">Take Profit:</label>
              <input type="number" id="take_profit" class="form-control" />
            </div>
            <div>
              <label for="stop_loss" class="form-label">Stop Loss:</label>
              <input type="number" id="stop_loss" class="form-control" />
            </div>
          </div>
          <div class="mt-4">
            <button type="button" class="btn btn-primary">Submit Order</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
  
  <script>
  import axios from "axios";
  
  export default {

    data() {
      return {
        symbol: "",
        side: "open",
        order_type: "limit",
        qty: "",
        price: "",
        time_in_force: "",
        tpsl: false,
      }
    },
    props: {
      selectedSymbol: {
        type: String,
        default: "",
      },
    },
    methods: {
      async submitOrder() {
        try {
          const response = await axios.post("http://localhost:8000/place_order", {
            symbol: this.symbol,
            side: this.side,
            order_type: this.order_type,
            qty: this.qty,
            price: this.price,
            time_in_force: this.time_in_force,
          });
          console.log("Order submitted successfully:", response.data);
        } catch (error) {
          console.error("Error submitting order:", error);
        }
      },
    },
  };
  </script>
  