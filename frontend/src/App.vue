<template>
  <div id="app">
    <SymbolSearch @selected-symbol="updateSelectedSymbol"/>
    <BybitOrderForm :selectedSymbol="selectedsymbol"/>
  </div>
</template>

<script>

import BybitOrderForm from "./components/BybitOrderForm.vue";
import SymbolSearch from "./components/SymbolSearch.vue";

import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";

export default {
  name: "App",
  components: {
    BybitOrderForm,
    SymbolSearch
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
