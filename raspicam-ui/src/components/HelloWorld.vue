<template>
  <div class="hello">
    <h1>{{ msg }}</h1>
    Hello
    <v-btn @click="setUpPusher">Hello</v-btn>
  </div>
</template>

<script>
export default {
  name: 'HelloWorld',
  props: {
    msg: String
  },
  methods: {
    setUpPusher () {
      // Enable pusher logging - don't include this in production
      Pusher.logToConsole = true;

      var addLog = function (message) {
        console.log(message);
        // XXX var logContainer = document.querySelector('#log');
        // XXX var p = document.createElement('p');
        // XXX var now = new Date();
        // XXX var logContent = document.createTextNode(
        // XXX   now.toISOString() + ' | ' + message);
        // XXX p.appendChild(logContent);
        // XXX logContainer.appendChild(p);
      };

      var pusher = new Pusher('49a7902e0bfdacbba646', {
        cluster: 'eu',
        encrypted: true
      });

      var channel = pusher.subscribe('motion-events');
      // XXX var audio = new Audio('{{url_for('static', filename='thrown.mp3')}}');
      channel.bind('motion-detected', function(data) {
        addLog(data.message);
        // XXX audio.play();
      });
    }
  }
}
</script>
