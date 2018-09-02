<template>
  <div class="mini-log">
    <h1>Log</h1>
    <p v-for="item in messages" :key="item.id">{{item}}</p>
  </div>
</template>

<script>
export default {
  name: 'MiniLog',
  props: {
    items: Array
  },
  computed: {
    messages () {
      let tail = this.items.slice(-6)
      let output = []
      tail.forEach(function (item) {
        output.push(new Date().toISOString() + ' | ' + item.payload.message)
      })
      return output
    }
  },
  methods: {
    pushItem (item) {
      let lastItem = this.items.slice(-1)[0]
      let lastIndex = 0;
      if (lastItem !== undefined) {
        lastIndex = lastItem.id
      }
      this.items.push({
        id: lastIndex + 1,
        payload: item
      })
    }
  }
}
</script>
