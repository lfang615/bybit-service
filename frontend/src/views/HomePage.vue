<template>
    <div id="app">
      
       
        <div class="row">
          <div class="col-12">
            <SymbolSearch @selected-symbol="updateSelectedSymbol" @risk-limit="updateRiskLimit"/>
          </div>
        </div>
      <div class="container mt-5">
        <div class="row">
            <div class="col-12 col-md-6 offset-md-3">
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
        <div v-if="open_close == 'open'" class="row pb-3">
          <div class="col-12 col-md-6 offset-md-3">
            <OpenOrderForm 
            :selectedSymbol="selectedsymbol"
            :symbolRiskLimit="symbolRiskLimit"
            @show-message-modal="openMessageModal"
            />
          </div>
        </div>
        <div v-if="open_close == 'close'" class="row pb-3">
          <div class="col-12 col-md-6 offset-md-3">
            <CloseOrderForm 
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
  
  import OpenOrderForm from "@/components/OpenOrderForm.vue";
  import CloseOrderForm from "@/components/CloseOrderForm.vue";
  import SymbolSearch from "@/components/SymbolSearch.vue";
  import OrdersGrid from "@/components/OrdersGrid.vue";
  import MessageModal from "@/components/MessageModal.vue";
  
  export default {
    name: "App",
    components: {
      OpenOrderForm,
      CloseOrderForm,
      SymbolSearch,
      OrdersGrid,
      MessageModal
    },
    data(){
      return {
        selectedsymbol: "",
        symbolRiskLimit: 0.00,
        isMessageModalOpen: false,
        messageModalTitle: "",
        messageModalMessage: "",
        open_close: "open"
      }
    },
    methods: {
      updateSelectedSymbol(symbol){
        this.selectedsymbol = symbol;
        console.log(this.selectedsymbol)
      },
      updateRiskLimit(riskLimit){
        this.symbolRiskLimit = Number(riskLimit["maxLeverage"]);
        console.log(this.symbolRiskLimit)
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
  