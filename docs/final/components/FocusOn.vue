<template>
  <div fixed inset-0 z-10>
    <div class="absolute inset-0 bg-#FBFCFD/70 fade-in" :style="{
      'maskImage': `radial-gradient(circle at ${left}px ${top}px, transparent ${radius - 10}px, black ${radius + 0}px)`
    }">
    </div>
    <div class="fade-in" border="3px red solid" rounded-full :style="{
      width: `${radius * 2}px`,
      height: `${radius * 2}px`,
      left: `${left - radius}px`,
      top: `${top - radius}px`
    }" absolute />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  left: number;
  top: number;
  radius: number;
}>();
</script>

<style scoped>
.slidev-nav-go-forward .fade-in {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.8);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>