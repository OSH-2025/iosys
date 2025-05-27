<template>
  <div class="flex flex-col h-screen bg-white">
    <!-- Title Bar -->
    <header class="bg-white text-black p-4 border-b border-gray-200 flex justify-between items-center">
      <h1 class="text-xl font-normal pl-2">IOSYS</h1>
      <!-- Status Display -->
      <div class="text-sm text-gray-600 flex space-x-4">
        <div v-for="(value, key) in status" :key="key" class="flex items-center space-x-1">
          <span class="font-medium">{{ key }}:</span>
          <span :class="{'text-green-600': value === 'ready' || value === 'ok', 'text-red-600': value?.includes('error') || value?.includes('offline')}">
            {{ value }}
          </span>
        </div>
      </div>
    </header>

    <!-- Main Content Area -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Left Sidebar - Chat -->
      <aside class="w-80 max-w-40% bg-white border-r border-gray-200 flex flex-col">
        <div class="flex-1 overflow-hidden">
          <!-- Chat messages component -->
          <Messages />
        </div>

        <!-- Mode Toggle -->
        <div class="mb-3 mx-4">
          <div class="flex bg-gray-100 rounded-md p-1">
            <button 
              @click="chatMode = 'chat'"
              :class="['flex-1 py-2 px-3 rounded text-sm transition-colors', 
                      chatMode === 'chat' ? 'bg-white text-black shadow-sm' : 'text-gray-600 hover:text-black']"
            >
              💬 Chat
            </button>
            <button 
              @click="chatMode = 'agent'"
              :class="['flex-1 py-2 px-3 rounded text-sm transition-colors', 
                      chatMode === 'agent' ? 'bg-white text-black shadow-sm' : 'text-gray-600 hover:text-black']"
            >
              🤖 Agent
            </button>
          </div>
        </div>

        <!-- Input and Submit Button -->
        <div class="m-4 mt-0">
          <input v-model="inputText" type="text"
            class="w-full border border-gray-200 rounded-md p-2 mb-3 focus:outline-none focus:border-black transition-colors duration-150"
            :placeholder="chatMode === 'chat' ? 'Enter text...' : 'Enter command...'" 
            @keyup.enter="handleSubmit" />
          <button @click="handleSubmit"
            class="w-full bg-black hover:bg-gray-800 text-white font-normal py-2 px-4 rounded-md transition duration-150">
            {{ chatMode === 'chat' ? 'Submit' : 'Execute' }}
          </button>
        </div>
      </aside>

      <!-- Right Main Content -->
      <main class="relative flex-1 bg-white">
        <!-- Main content will go here -->
        <GraphView />
        <FilePreview />
      </main>
    </div>

    <!-- Error Popup -->
    <div v-if="errorMessage"
      class="fixed bottom-4 right-4 bg-red-100 border border-red-300 shadow-md p-4 rounded-md text-red-700">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useIntervalFn, useLocalStorage } from '@vueuse/core';
import Messages from './components/Messages.vue';
import GraphView from './components/GraphView.vue';
import rpc, { ApiResponse } from './rpc';
import { errorMessage, messages } from './states';
import FilePreview from './components/FilePreview.vue';

const inputText = ref('');
const chatMode = useLocalStorage<'chat' | 'agent'>('iosys.mode', 'chat');

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
      
      // Format agent response for display
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
  } catch (e) {
    inputText.value ||= input;
    messages.pop();
    messages.push({ content: '❌ ' + e, fromUser: false });
  }
};

let errorTimeout: number | null = null;
watch(
  errorMessage,
  (newValue) => {
    if (newValue) {
      if (errorTimeout) clearTimeout(errorTimeout);
      errorTimeout = window.setTimeout(() => {
        errorMessage.value = null;
        errorTimeout = null;
      }, 5000); // Popup disappears after 3 seconds
    }
  },
  { immediate: true }
);

const status = ref<Partial<ApiResponse<"status">>>({});
useIntervalFn(
  async () => {
    try {
      status.value = await rpc.status({});
    } catch (e) {
      status.value = {
        server: 'offline',
      }
    }
  },
  10000,
  { immediate: true, immediateCallback: true }
);
</script>
