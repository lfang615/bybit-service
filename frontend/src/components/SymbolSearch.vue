<template>
    <nav class="navbar bg-body-tertiary">
    <div class="container">
      <form class="d-flex">
        <input class="form-control me-2" type="search" placeholder="Search" aria-label="Search"
          v-model="searchText"
          @focusin="isActive = true"
          @input="filterSymbols">
        <!-- <button class="btn btn-outline-success" type="submit"
          @click="isActive = false"
        >Select</button> -->
        <div class="list-group search-results">
        <button
            v-for="symbol in filteredSymbols"
            :key="symbol"
            class="list-group-item list-group-item-action"
            :class="{ visible: isActive, hidden: !isActive }"
            @click="onSelection(symbol)"> 
            {{ symbol }}
        </button>
      </div>       
      </form>
      
    </div>
  </nav>
</template>

<script>
import axios from "axios";

export default {
  computed: {
    apiUrl() {
      return `${process.env.VUE_APP_API_BASE_URL}`;
    }
  },
  data() {
    return {
      searchText: "",
      symbols: [],
      filteredSymbols: [],
      isActive: true,
    };
  },
  async created() {
    await this.fetchSymbols();
  },
  methods: {
    async fetchSymbols() {
      try {
        const response = await axios.get(this.apiUrl + "/symbols");
        this.symbols = response.data;
      } catch (error) {
        console.error("Error fetching symbols:", error);
      }
    },
    async fetchRiskLimit(symbol){
      try {
        const response = await axios.get(this.apiUrl + "/risk_limits" + "/" + symbol);
        return response.data;
      } catch (error) {
        console.error("Error fetching risk limit:", error);
      }
    },
    filterSymbols() {
      const searchTextLowerCase = this.searchText.toLowerCase();
      this.filteredSymbols = this.symbols.filter((symbol) =>
        symbol.toLowerCase().startsWith(searchTextLowerCase)
      );
    },
    async onSelection(symbol) {
      this.searchText = symbol;
      this.filteredSymbols = [];
      this.$emit('selected-symbol', symbol)
      const riskLimit = await this.fetchRiskLimit(symbol);
      this.$emit('risk-limit', riskLimit)

    },
    clearSearch() {
      this.searchText = "";
      this.filteredSymbols = [];
    },
  },
};
</script>

<style scoped>
.search-results {
  max-height: calc(4 * 3rem); /* Adjust this to the height of your list items */
  overflow-y: auto;
  position: fixed;
  top: 3rem;
  z-index: 100;
}

.visible {
  display: block;
}

.hidden {
  display: none;
}
</style>