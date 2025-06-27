<template>
  <!-- Mode Toggle -->
  <!-- <div class="mb-3 mx-4">
    <div class="flex bg-gray-100 rounded-md p-1">
      <button @click="chatMode = 'chat'" :class="['flex-1 py-2 px-3 rounded text-sm transition-colors',
        chatMode === 'chat' ? 'bg-white text-black shadow-sm' : 'text-gray-600 hover:text-black']">
        💬 Chat
      </button>
      <button @click="chatMode = 'agent'" :class="['flex-1 py-2 px-3 rounded text-sm transition-colors',
        chatMode === 'agent' ? 'bg-white text-black shadow-sm' : 'text-gray-600 hover:text-black']">
        🤖 Agent
      </button>
    </div>
  </div> -->

  <!-- Input and Submit Button -->
  <div class="m-4 mt-0">
    <input v-model="inputText" type="text"
      class="w-full border border-gray-200 rounded-md p-2 mb-3 focus:outline-none focus:border-black transition-colors duration-150"
      :placeholder="chatMode === 'chat' ? 'Enter text...' : 'Enter command...'" @keyup.enter="handleSubmit" />
    <button @click="handleSubmit"
      class="w-full bg-black hover:bg-gray-800 text-white font-normal py-2 px-4 rounded-md transition duration-150">
      {{ chatMode === 'chat' ? 'Submit' : 'Execute' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useLocalStorage } from '@vueuse/core';
import rpc from '../rpc';
import { messages, refreshStatus } from '../states';

const inputText = ref('');
const chatMode = ref('agent'); // useLocalStorage<'chat' | 'agent'>('iosys.mode', 'chat');

const handleSubmit = async () => {
  const input = inputText.value.trim();
  if (!input) return;
  inputText.value = '';

  messages.push(
    { content: input, fromUser: true },
    { content: '...', fromUser: false },
  );

  try {
    if (chatMode.value === 'chat') {
      const { response } = await rpc.chat({ input });
      messages.pop();
      messages.push({ content: response, fromUser: false });
    } else {
      const result = await rpc.agent({ command: input });
      messages.pop();

      let responseText = '';
      if (result.status === 'success') {
        responseText = `✅ ${result.message || 'Command executed successfully'}`;
        if (result.data) {
          responseText += `\n\nResult:\n\n<pre>\n${JSON.stringify(result.data, null, 2)}\n</pre>`;
        }
      } else {
        responseText = `❌ ${result.message || 'Command failed'}`;
      }

      messages.push({ content: responseText, fromUser: false });
    }
    setTimeout(refreshStatus, 100);
  } catch (e) {
    inputText.value ||= input;
    messages.pop();
    messages.push({ content: '❌ ' + e, fromUser: false });
  }
};
</script>
