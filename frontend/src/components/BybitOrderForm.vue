<!-- frontend/src/components/BybitOrderForm.vue -->
<template>
  <div class="container mt-5">
    <div class="row">
      <div class="col">
        <ul class="nav nav-tabs">
          <li class="nav-item">
            <a class="nav-link" :class="{ active: open_close == 'open'}" @click="open_close = 'open'" href="#">Open</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" :class="{ active: open_close == 'close'}" @click="open_close = 'close'" href="#">Close</a>
          </li>
        </ul>
      </div>
    </div>

    <div class="row mt-2">
      <div class="col">
        <div class="btn-group mt-3" role="group" aria-label="Basic outlined example">
          <button type="button" class="btn btn-outline-primary"
           :class="{ active: orderType == 'Limit'}"
           @click="orderType = 'Limit'">Limit</button>
          <button type="button" class="btn btn-outline-primary" 
          :class="{ active: orderType == 'Market'}"
          @click="orderType = 'Market'">Market</button>
          <button type="button" class="btn btn-outline-primary" 
            :class="{ active: orderType == 'conditional'}"
            @click="orderType = 'conditional'">Conditional</button>
        </div>    
      </div>
    </div>

    <div class="row mt-4">
      <div class="col">
        <form @submit.prevent="setLeverage">
          <div class="row mb-3">
            <div class="col">
              <label for="buy-leverage" class="form-label">Buy Leverage</label>
              <input type="text" id="buy-leverage" class="form-control" v-model="buyLeverage" />
            </div>
          <div class="col">
            <label for="sell-leverage" class="form-label">Sell Leverage</label>
            <input type="text" id="sell-leverage" class="form-control" v-model="sellLeverage" />
        </div>
      </div>
      <button type="submit" class="btn btn-primary mb-3">Set Leverage</button>
    </form>
        <form @submit.prevent="submitOrder">
          <div>
            <label for="symbol" class="form-label">Symbol:</label>
            <input type="text" id="symbol" class="form-control" :value="selectedSymbol" disabled required />
          </div>
          <div>
            <label for="qty" class="form-label">Quantity:</label>
            <input type="text" id="qty" class="form-control" v-model="qty" required />
          </div>
          <div>
            <label for="price" class="form-label">Price:</label>
            <input type="text" step="0.000001" id="price" class="form-control" v-model="price" required />
          </div>
         
          <div>
            <label for="time_in_force" class="form-label">Time in Force:</label>
            <select id="time_in_force" class="form-select" v-model="time_in_force" required>
              <option value="GoodTillCancel" selected>Good Till Cancel</option>
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
              <input type="text" step="0.000001" id="take_profit" class="form-control" v-model="take_profit"/>
            </div>
            <div>
              <label for="stop_loss" class="form-label">Stop Loss:</label>
              <input type="text" step="0.000001" id="stop_loss" class="form-control" v-model="stop_loss" />
            </div>
          </div>
          <div class="mt-4 btn-group">
            <button type="submit" name="btn-submitOrder" class="btn btn-success"
              @click="side = 'Buy'">Open Long</button>
            <button type="submit" name="btn-submitOrder" class="btn btn-danger"
              @click="side = 'Sell'">Open Short</button>
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
        open_close: "open",
        symbol: "",
        side: "",
        orderType: "Limit",
        qty: "",
        price: "",
        time_in_force: "",
        tpsl: false,
        take_profit: "",
        stop_loss: "",
        buyLeverage: "",
        sellLeverage: "",
      }
    },
    props: {
      selectedSymbol: {
        type: String,
        default: "",
      },
    },
    methods: {
      async setLeverage() {
        try {
          const payload = {
            buyLeverage: this.buyLeverage,
            sellLeverage: this.sellLeverage,
          };
          await axios.post('http://localhost:8000/set_leverage', payload);
          console.log('Leverage set successfully');
        } catch (error) {
          console.error('Failed to set leverage:', error);
        }
      },
      async submitOrder() {
        try {
          const response = await axios.post("http://localhost:8000/place_order", {
            symbol: this.$props.selectedSymbol,
            side: this.side,
            orderType: this.orderType,
            qty: this.qty,
            price: this.price,
            timeInForce: this.time_in_force,
          });
          console.log("Order submitted successfully:", response.data);
        } catch (error) {
          console.error("Error submitting order:", error);
        }
      },
    },
  };
  </script>
  