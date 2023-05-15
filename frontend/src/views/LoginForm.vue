<template>
    <div>
      <form @submit.prevent="handleLogin">
        <div class="mb-3">
          <label for="username" class="form-label">Username:</label>
          <input type="text" class="form-control" id="username" v-model="username" />
        </div>
        <div class="mb-3">
          <label for="exampleFormControlTextarea1" class="form-label">Password</label>
          <input type="password" class="form-control" id="password" v-model="password" />
        </div>
        <button type="submit">Login</button>
      </form>
    </div>
  </template>
  
  <script>
  import AuthService from '@/services/authService';
  
  export default {
    data() {
      return {
        username: '',
        password: '',
      };
    },
    methods: {
      handleLogin() {
        AuthService.login({
          username: this.username,
          password: this.password,
        })
        .then(
          () => {
            this.$router.push({ name: 'Home' });
          },
          error => {
            this.message = (error.response.data && error.response.data.message) || error.message || error.toString();
          }
        );
      },
    },
  };
  </script>
  