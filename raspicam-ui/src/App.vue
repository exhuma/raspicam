<template>
  <div id="app">
    <img src="http://rpi-cam:5000/live_feed">
    <Pusher appKey="49a7902e0bfdacbba646" @messageReceived="logMessage"></Pusher>
    <v-btn @click="testItem">Push Item</v-btn>
    <MiniLog ref="miniLog" :items="logEntries"></MiniLog>
  </div>
</template>

<script>
import HelloWorld from './components/HelloWorld.vue'
import Pusher from './components/Pusher.vue'
import MiniLog from './components/MiniLog.vue'

export default {
  name: 'app',
  data () {
    return {
      logEntries: []
    }
  },
  methods: {
    testItem () {
      this.$refs.miniLog.pushItem({'message': 123})
    },
    logMessage (payload) {
      console.log(payload)
      this.$refs.miniLog.pushItem(payload)
    }
  },
  components: {
    HelloWorld,
    Pusher,
    MiniLog
  }
}
</script>

<style>
#app {
  font-family: 'Avenir', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
</style>
