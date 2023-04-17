<template>
  <div id="app">
    <div class="container">
      <div class="row">
        <div class="col-12">
          <SymbolSearch @selected-symbol="updateSelectedSymbol" />
        </div>
      </div>
      <div class="row pb-3">
        <div class="col-12 col-md-6 offset-md-3">
          <BybitOrderForm :selectedSymbol="selectedsymbol" />
        </div>
      </div>
      <hr class="border border-primary">
      <div class="row pt-3">
        <div class="col-12 col-md-6 offset-md-3">
          <OrdersGrid />
        </div>
      </div>
    </div>
  </div>
</template>

<script>

import BybitOrderForm from "./components/BybitOrderForm.vue";
import SymbolSearch from "./components/SymbolSearch.vue";
import OrdersGrid from "./components/OrdersGrid.vue";

import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";

export default {
  name: "App",
  components: {
    BybitOrderForm,
    SymbolSearch,
    OrdersGrid
  },
  data(){
    return {
      selectedsymbol: ""
    }
  },
  methods: {
    updateSelectedSymbol(symbol){
      this.selectedsymbol = symbol;
      console.log(this.selectedsymbol)
    }
  }
};
</script>
