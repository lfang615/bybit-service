<template>
    <div class="row mt-2">
        <div class="col">
            <div class="btn-group mt-3" role="group" aria-label="Basic outlined example">
                <button type="button" class="btn btn-outline-primary"
                :class="{ active: orderType == 'Limit'}"
                @click="orderType = 'StopLimit'">Stop Limit</button>
                <button type="button" class="btn btn-outline-primary"
                :class="{ active: orderType == 'Market'}"
                @click="orderType = 'StopMarket'">Stop Market</button>
                <button type="button" class="btn btn-outline-primary"
                :class="{ active: orderType == 'Market'}"
                @click="orderType = 'TPSL_Market'">TPSL Market</button>
            </div>
        </div>
    </div>
   <div class="row mt-4">
        <div class="col">
            <!-- TPSL Market Form -->
            <form v-if="orderType == 'TPSL_Market'" @submit.prevent="setStop">
                <div class="row mb-3">
                    <div class="col">
                        <label for="takeProfit" class="form-label">Take Profit Trigger Price</label>
                        <input type="text" id="takeProfit" v-model="takeprofit" class="form-control" />
                    </div>
                    <div class="col">
                        <label for="stopLoss" class="form-label">Stop Loss Trigger Price</label>
                        <input type="text" id="stopLoss" v-model="stoploss" class="form-control" />
                    </div>
                </div>
                <button type="submit" class="btn btn-primary mb-3">Set TPSL</button>
            </form>
                <hr class="border border-primary">

            <!-- StopMarket Form -->
            <form v-if="orderType == 'StopMarket'" @submit.prevent="submitOpenOrder">
                <!-- Your open order form fields here -->
                <div>
                    <label for="symbol" class="form-label">Symbol:</label>
                    <input type="text" id="symbol" class="form-control" :value="selectedSymbol" disabled required />
                </div>
                <div>
                    <label for="qty" class="form-label">Quantity:</label>
                    <input type="text" id="qty" class="form-control" v-model="qty" required />
                </div>
                <div>
                    <label for="triggerPrice" class="form-label">Trigger Price:</label>
                    <input type="text" step="0.000001" id="triggerPrice" class="form-control" v-model="triggerPrice" required />
                </div>
                <div>
                    <select v-model="timeInForce" :disabled="isTimeInForceDisabled" class="form-select">
                        <option disabled>Open this select menu</option>
                        <option v-for="option in timeInForceOptions" :key="option" :value="option">
                            {{ option }}
                        </option>
                    </select>
                </div>
                <div class="mt-4 btn-group">
                    <button type="submit" name="btn-submitOrder" class="btn btn-success"
                    @click="side = 'Buy'">Close Long</button>
                    <button type="submit" name="btn-submitOrder" class="btn btn-danger"
                    @click="side = 'Sell'">Close Short</button>
                </div>
            </form>
            
            <!-- StopLimit Order Form -->
            <form v-if="orderType == 'StopLimit'" @submit.prevent="submitCloseOrder">
                <div>
                    <label for="qty" class="form-label">Quantity:</label>
                    <input type="text" id="takeProfitPrice" class="form-control" v-model="tri" required />
                </div>
                <div>
                    <label for="triggerPrice" class="form-label">Trigger Price:</label>
                    <input type="text" step="0.000001" id="triggerPrice" class="form-control" v-model="triggerPrice" required />
                </div>
                <div>
                    <label for="price" class="form-label">Limit Price:</label>
                    <input type="text" step="0.000001" id="price" class="form-control" v-model="price" required />
                </div>
                <div class="mt-4 btn-group">
                    <button type="submit" name="btn-submitOrder" class="btn btn-success"
                    @click="side = 'Buy'">Close Short</button>
                    <button type="submit" name="btn-submitOrder" class="btn btn-danger"
                    @click="side = 'Sell'">Close Long</button>
                </div>
            </form>
        </div>
    </div>
</template>
  
  <script>
  import axios from "axios";
  export default {
    name: "CloseOrderForm",
    data() {
        return {
            symbol: "",
            side: "",
            orderType: "Limit",
            qty: "",
            price: "",
            timeInForce: "",
            triggerDirection: "",
            triggerPrice: "",
            takeprofit: "",
            stoploss: "",
            reduceOnly: false,
            closeOnTrigger: false,
            tpsl: false,
            buyLeverage: "",
            sellLeverage: "",
            showModal: false,
            modalType: 'error', // or 'success'
            modalMessage: "",
            // leverage range slider
            buyLeverageSliderValue: 0,
            sellLeverageSliderValue: 0,
            selectedtimeInForce: "",
            timeInForceOptions: [
                "GoodTillCancel",
                "ImmediateOrCancel",
                "FillOrKill",
            ],
            isTimeInForceDisabled: false,
        }
    },
    props: {
        selectedSymbol: {
            type: String,
            default: "",
        }
    },
    emits: ["showMessageModal"],
    methods: {
        async setStop(){
            try {
                const payload = {
                    symbol: this.$props.selectedSymbol,
                    buyLeverage: this.buyLeverage,
                    sellLeverage: this.sellLeverage,
                };
                const response = await axios.post(`${process.env.VUE_APP_API_BASE_URL}/set_leverage`, payload);
                if(response.status === 200) {
                    this.showMessageModal('Success', 'Leverage set successfully!');
                }else {
                    this.showMessageModal('Error', response.data['retMsg']);
                }
                console.log('Leverage set successfully');
            } catch (error) {
                this.showMessageModal('Error', error.message)
                console.error('Failed to set leverage:', error);
            }
        }
    }
  };
  </script>
  