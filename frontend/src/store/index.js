import { createStore } from 'vuex'
import AuthService from '@/services/authService';

export default createStore({
  state: {
    status: '',
    user: localStorage.getItem('user') || '',
    errorMessage: null,
  },
  mutations: {
    auth_request(state) {
      state.status = 'loading';
    },
    auth_success(state, user) {
      state.status = 'success';
      state.user = user;
    },
    auth_error(state, error) {
      state.status = 'error';
      state.errorMessage = error;
    },
    logout(state) {
      state.status = '';
      state.user = '';
    },
  },
  actions: {
    login({ commit }, user) {
      return new Promise((resolve, reject) => {
        commit('auth_request');
        AuthService.login(user)
          .then(resp => {
            const user = resp.data;
            localStorage.setItem('user', JSON.stringify(user));
            commit('auth_success', user);
            resolve(resp);
          })
          .catch(err => {
            commit('auth_error', err);
            localStorage.removeItem('user');
            reject(err);
          });
      });
    },
    logout({ commit }) {
      return new Promise(resolve => {
        commit('logout');
        localStorage.removeItem('user');
        resolve();
      });
    },
  },
})
