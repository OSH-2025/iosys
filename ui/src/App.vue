<template>
  <div class="flex flex-col h-screen bg-white">
    <!-- Title Bar -->
    <header class="bg-white text-black p-4 border-b border-gray-200 flex justify-between items-center">
      <h1 class="text-xl font-normal pl-2">IOSYS</h1>
      <!-- Status Display -->
      <div class="text-sm text-gray-600 flex space-x-4">
        <div v-for="(value, key) in status" :key="key" class="flex items-center space-x-1">
          <template v-if="typeof value === 'string'">
            <span class="font-medium">{{ key }}:</span>
            <span
              :class="{ 'text-green-600': value === 'ready' || value === 'ok', 'text-red-600': value?.includes('error') || value?.includes('offline') }">
              {{ value }}
            </span>
          </template>
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
        <ChatBox />
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
import { watch } from 'vue';
import Messages from './components/Messages.vue';
import GraphView from './components/GraphView.vue';
import { errorMessage, status } from './states';
import FilePreview from './components/FilePreview.vue';
import ChatBox from './components/ChatBox.vue';

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
</script>
