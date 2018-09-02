<template></template>

<script>
export default {
  name: 'Pusher',
  props: {
    appKey: String
  },
  created: function () {
    // Enable pusher logging - don't include this in production
    Pusher.logToConsole = true;
    this.$emit('messageReceived', {'foo': 'bar'});

    var pusher = new Pusher(this.appKey, {
      cluster: 'eu',
      encrypted: true
    });

    var that = this;
    var channel = pusher.subscribe('motion-events');
    // XXX var audio = new Audio('{{url_for('static', filename='thrown.mp3')}}');
    channel.bind('motion-detected', function(data) {
      that.$emit('messageReceived', data);
      // XXX that.addLog(data.message);
      // XXX audio.play();
    });
  }
}
</script>

