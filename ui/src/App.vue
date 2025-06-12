<template>
  <div class="flex flex-col h-screen bg-white">
    <!-- Title Bar -->
    <header class="bg-white text-black p-4 border-b-2 border-gray-200 flex justify-between items-center">
      <h1 class="text-xl font-normal pl-2">IOSYS</h1>
      <!-- Status Display -->
      <div class="text-sm text-gray-600 flex space-x-4">
        <template v-for="(value, key) in status" :key="key">
          <div v-if="typeof value === 'string'" class="flex items-center gap-x-1">
            <span class="font-medium">{{ key }}:</span>
            <span
              :class="{ 'text-green-600': value === 'ready' || value === 'ok', 'text-red-600': value?.includes('error') || value?.includes('offline') }">
              {{ value }}
            </span>
          </div>
          <button 
            v-else-if="key === 'mcp_servers'"
            class="flex items-center hover:bg-gray-200 gap-x-1 transition-colors duration-150 px-2 py-2 my--2 rounded-md border-2 border-gray-200"
            :class="showMcpPanel ? 'bg-gray-100' : ''"
            @click="showMcpPanel = !showMcpPanel"
            title="Toggle MCP Servers"
          >
            <span class="font-medium">MCP Servers:</span>
            <span class="text-green-600">{{ Object.keys(value ?? {}).length }}</span>
          </button>
        </template>
      </div>
    </header>

    <!-- Main Content Area -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Left Sidebar - Chat -->
      <aside :style="{ width: sidebarWidth + 'px' }" class="bg-white border-r-2 border-gray-200 flex flex-col"
        style="min-width: 200px; max-width: 600px;">
        <div class="flex-1 overflow-hidden">
          <!-- Chat messages component -->
          <Messages />
        </div>
        <ChatBox />
      </aside>

      <!-- Resize Handle -->
      <div class="relative w-0 z-100">
        <div @mousedown="startResize"
          class="absolute inset-x--3px inset-y-0 hover:bg-gray-300 cursor-col-resize transition-colors duration-150">
        </div>
      </div>

      <!-- Right Main Content -->
      <main class="relative flex-1 bg-white">
        <!-- Main content will go here -->
        <FilePreview />
        <McpServers v-show="showMcpPanel" />
        <GraphView v-show="!showMcpPanel" />
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
import Messages from './components/Messages.vue';
import GraphView from './components/GraphView.vue';
import { errorMessage, status } from './states';
import FilePreview from './components/FilePreview.vue';
import ChatBox from './components/ChatBox.vue';
import { useDynamicSplitter } from './composables/useDynamicSplitter';
import McpServers from './components/McpServers.vue';

const showMcpPanel = ref(false);

// Sidebar width with persistent storage and resize functionality
const { width: sidebarWidth, startResize } = useDynamicSplitter({
  storageKey: 'sidebar-width',
  defaultWidth: 320,
  minWidth: 200,
  maxWidth: 800
});

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
