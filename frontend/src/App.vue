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
          <BybitOrderForm 
          :selectedSymbol="selectedsymbol"
          @show-message-modal="openMessageModal"
          />
        </div>
      </div>
      <hr class="border border-primary col-12 col-md-6 offset-md-3">
      <div class="row pt-3">
        <div class="col-12 col-md-8 offset-md-3">
          <OrdersGrid @show-message-modal="openMessageModal"/>
        </div>
      </div>
    </div>
    <MessageModal
      :isOpen="isMessageModalOpen"
      :title="messageModalTitle"
      :message="messageModalMessage"
      @close="closeMessageModal"
      ref="messageModal"
      />
  </div>
</template>

<script>

import BybitOrderForm from "./components/BybitOrderForm.vue";
import SymbolSearch from "./components/SymbolSearch.vue";
import OrdersGrid from "./components/OrdersGrid.vue";
import MessageModal from "./components/MessageModal.vue";

import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";

export default {
  name: "App",
  components: {
    BybitOrderForm,
    SymbolSearch,
    OrdersGrid,
    MessageModal
  },
  data(){
    return {
      selectedsymbol: "",
      isMessageModalOpen: false,
      messageModalTitle: "",
      messageModalMessage: "",
    }
  },
  methods: {
    updateSelectedSymbol(symbol){
      this.selectedsymbol = symbol;
      console.log(this.selectedsymbol)
    },
    openMessageModal(args) {
      this.messageModalTitle = args.messageModalTitle;
      this.messageModalMessage = args.messageModalMessage;
      this.isMessageModalOpen = true;
    },
    closeMessageModal() {
      this.isMessageModalOpen = false;
    },
    toggleMessageModal() {
      this.$refs.messageModal.isOpen = !this.$refs.messageModal.isOpen;
    },
  }
};
</script>
