<template>
  <div ref="messagesContainer" class="messages-container flex flex-col gap-3 overflow-y-auto p-4">
    <div v-for="(message, index) in messages" :key="index" :class="[
      'message p-3 rounded-lg max-w-[85%]',
      message.fromUser ? 'self-end bg-black text-white' : 'self-start bg-gray-100 text-black'
    ]">
      <Markdown :content="message.content" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { messages } from '../states';
import Markdown from './Markdown.vue';
import { watch, nextTick, useTemplateRef } from 'vue';

const messagesContainer = useTemplateRef('messagesContainer');

// Watch for new messages and auto-scroll to bottom
watch(messages, async () => {
  if (messagesContainer.value) {
    await nextTick();
    console.log('New message added, scrolling to bottom');
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}, { deep: true });
</script>

<style scoped>
.messages-container {
  height: calc(100% - 1rem);
  scrollbar-width: thin;
}

.messages-container::-webkit-scrollbar {
  width: 4px;
}

.messages-container::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.message {
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  animation: fadeIn 0.2s ease-in-out;
  transition: all 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(5px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
