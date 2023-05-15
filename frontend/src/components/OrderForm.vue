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
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col">
                <!-- Your leverage form here -->
                <form v-if="open_close == 'open'" @submit.prevent="setLeverage">
                    <div class="row mb-3">
                        <div class="col">
                            <label for="buy-leverage" class="form-label">Buy Leverage</label>
                            <!-- <input type="text" id="buy-leverage" class="form-control" v-model="buyLeverage" />-->
                            <input type="range" id="buy-leverage" v-model="buyLeverageSliderValue" class="form-range" min="0" :max="symbolRiskLimit" step="0.5" />
                            <span class="badge bg-primary">{{ buyLeverageSliderValue }}</span>
                        </div>
                        <div class="col">
                            <label for="sell-leverage" class="form-label">Sell Leverage</label>
                            <!-- <input type="text" id="sell-leverage" class="form-control" v-model="sellLeverage" /> -->
                            <input type="range" id="sell-leverage" class="form-range" min="0" max="100" step="1" v-model="sellLeverageSliderValue" />
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary mb-3">Set Leverage</button>
                </form>
                <hr class="border border-primary">
                
                <!-- Open Order Form -->
                <form v-if="open_close == 'open'" @submit.prevent="submitOpenOrder">
                    <!-- Your open order form fields here -->
                    <div>
                        <label for="symbol" class="form-label">Symbol:</label>
                        <input type="text" id="symbol" class="form-control" :value="selectedSymbol" disabled required />
                    </div>
                    <div>
                        <label for="qty" class="form-label">Quantity:</label>
                        <input type="text" id="qty" class="form-control" v-model="qty" required />
                    </div>
                    <div v-if="orderType == 'Limit'">
                        <label for="price" class="form-label">Price:</label>
                        <input type="text" step="0.000001" id="price" class="form-control" v-model="price" required />
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
                        @click="side = 'Buy'">Open Long</button>
                        <button type="submit" name="btn-submitOrder" class="btn btn-danger"
                        @click="side = 'Sell'">Open Short</button>
                    </div>
                </form>
                
                <!-- Close Order Form -->
                <form v-if="open_close == 'close'" @submit.prevent="submitCloseOrder">
                    <!-- Your close order form fields here -->
                    
                    <div>
                        <label for="qty" class="form-label">Quantity:</label>
                        <input type="text" id="takeProfitPrice" class="form-control" v-model="tri" required />
                    </div>
                    <div v-if="orderType == 'Limit'">
                        <label for="price" class="form-label">Price:</label>
                        <input type="text" step="0.000001" id="price" class="form-control" v-model="price" required />
                    </div>
                    <div class="mt-4 btn-group">
                        <button type="submit" name="btn-submitOrder" class="btn btn-success"
                        @click="side = 'Buy'">Close Long</button>
                        <button type="submit" name="btn-submitOrder" class="btn btn-danger"
                        @click="side = 'Sell'">Close Short</button>
                    </div>
                </form>
            </div>
        </div>
        
        <!-- Error Modal -->
        <div class="modal" tabindex="-1" :class="{ 'show': showModal }" style="display: block;" v-if="showModal">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" v-if="modalType === 'success'">Success</h5>
                        <h5 class="modal-title" v-if="modalType === 'error'">Error</h5>
                        <button type="button" class="btn-close" @click="showModal = false"></button>
                    </div>
                    <div class="modal-body">
                        <p :class="{ 'text-success': modalType === 'success', 'text-danger': modalType === 'error' }">
                            {{ modalMessage }}
                        </p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" @click="showModal = false">Close</button>
                    </div>
                </div>
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
        }
    },
    computed: {
        isTimeInForceDisabled() {
        return this.open_close === 'close';
        },
    },
    watch: {
        open_close(newValue) {
        if (newValue === 'close') {
            this.selectedTimeInForce = 'ImmediateOrCancel';
        } else if (this.selectedTimeInForce === 'ImmediateOrCancel') {
            this.selectedTimeInForce = 'GoodTillCancel';
        }
        },
    },
    created() {
        this.selectedTimeInForce = 'GoodTillCancel'; // Set the default value
    },
    props: {
        selectedSymbol: {
            type: String,
            default: "",
        },
        symbolRiskLimit: {
            type: Number,
            default: 0,
        },
    },
    methods: {
        async setLeverage() {
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
        },
        async submitOrder() {
            if (this.$props.selectedSymbol === "") {
                this.showMessageModal("Error", "Symbol field cannot be empty!");
                return;
            }
            try {
                const response = await axios.post(`${process.env.VUE_APP_API_BASE_URL}/place_order`,
                {
                    symbol: this.$props.selectedSymbol,
                    side: this.side,
                    orderType: this.orderType,
                    qty: this.qty,
                    price: this.price,
                    timeInForce: this.timeInForce,
                });
                
                if(response.status === 200) {
                    this.showMessageModal('Success', 'Order placed successfully!')
                }else {
                    this.showMessageModal('Error', response.data['retMsg'])
                }
                console.log("Order submitted successfully:", response.data);
            } catch (error) {
                this.showMessageModal('Error', error.message)
                console.error("Error submitting order:", error);
            }
        },
        showMessageModal(messageModalTitle, messageModalMessage) {
            this.$emit('show-message-modal', {'messageModalTitle': messageModalTitle, 'messageModalMessage': messageModalMessage})
        },
    },
};
</script>
