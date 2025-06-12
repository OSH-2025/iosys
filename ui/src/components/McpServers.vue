<template>
  <div class="p-6 max-w-4xl mx-auto">
    <!-- Header -->
    <div class="mb-6">
      <h2 class="text-2xl font-semibold text-gray-900 mb-2">MCP Servers</h2>
      <p class="text-gray-600 text-sm">Manage Model Context Protocol servers for enhanced functionality</p>
    </div>

    <!-- Add Server Form -->
    <div class="bg-white border border-gray-200 rounded-lg p-4 mb-6">
      <div class="flex gap-3">
        <input
          v-model="newServerUrl"
          type="text"
          placeholder="Enter MCP server URL..."
          name=""
          class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          @keyup.enter="addServer"
          :disabled="isLoading"
        />
        <button
          @click="addServer"
          :disabled="!newServerUrl.trim() || isLoading"
          class="px-4 py-2 text-sm font-medium text-white bg-black rounded-md hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {{ isLoading ? 'Adding...' : 'Add Server' }}
        </button>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="errorMsg" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <div class="flex items-center gap-2">
        <div class="w-4 h-4 text-red-500">⚠</div>
        <p class="text-red-700 text-sm">{{ errorMsg }}</p>
      </div>
    </div>

    <!-- Success Message -->
    <div v-if="successMsg" class="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
      <div class="flex items-center gap-2">
        <div class="w-4 h-4 text-green-500">✓</div>
        <p class="text-green-700 text-sm">{{ successMsg }}</p>
      </div>
    </div>

    <!-- Server List -->
    <div class="bg-white border border-gray-200 rounded-lg">
      <div class="px-4 py-3 border-b border-gray-200">
        <h3 class="text-sm font-medium text-gray-900">
          Active Servers ({{ servers.length }})
        </h3>
      </div>
      
      <div v-if="servers.length === 0" class="p-8 text-center">
        <div class="text-gray-400 mb-2">
          <div class="w-12 h-12 mx-auto mb-3 bg-gray-100 rounded-full flex items-center justify-center">
            <div class="w-6 h-6">⚡</div>
          </div>
        </div>
        <p class="text-gray-500 text-sm">No MCP servers configured</p>
        <p class="text-gray-400 text-xs mt-1">Add a server URL above to get started</p>
      </div>

      <div v-else class="divide-y divide-gray-100">
        <div
          v-for="(server, index) in servers"
          :key="server"
          class="px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
        >
          <div class="flex items-center gap-3 flex-1 min-w-0">
            <div class="w-2 h-2 bg-green-500 rounded-full flex-shrink-0"></div>
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium text-gray-900 truncate">{{ server }}</p>
              <p class="text-xs text-gray-500">Server #{{ index + 1 }}</p>
            </div>
          </div>
          
          <button
            @click="removeServer(server)"
            :disabled="isLoading"
            class="ml-3 px-3 py-1 text-xs font-medium text-red-600 hover:text-red-700 hover:bg-red-50 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Remove
          </button>
        </div>
      </div>
    </div>

    <!-- Footer Info -->
    <div class="mt-4 text-xs text-gray-500">
      <p>MCP servers provide additional tools and capabilities to the agent system.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import apis from '../rpc'

const servers = ref<string[]>([])
const newServerUrl = ref('')
const isLoading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

const clearMessages = () => {
  errorMsg.value = ''
  successMsg.value = ''
}

const showSuccess = (message: string) => {
  clearMessages()
  successMsg.value = message
  setTimeout(() => { successMsg.value = '' }, 3000)
}

const showError = (message: string) => {
  clearMessages()
  errorMsg.value = message
  setTimeout(() => { errorMsg.value = '' }, 5000)
}

const loadServers = async () => {
  try {
    const response = await apis.status({})
    servers.value = response.mcp_servers || []
  } catch (error) {
    console.error('Failed to load MCP servers:', error)
    showError('Failed to load server list')
  }
}

const addServer = async () => {
  if (!newServerUrl.value.trim() || isLoading.value) return
  
  isLoading.value = true
  clearMessages()
  
  try {
    const response = await apis.mcpAdd({ server_url: newServerUrl.value.trim() })
    servers.value = response.servers
    newServerUrl.value = ''
    showSuccess(response.message)
  } catch (error) {
    console.error('Failed to add MCP server:', error)
    showError('Failed to add server. Please check the URL and try again.')
  } finally {
    isLoading.value = false
  }
}

const removeServer = async (serverUrl: string) => {
  if (isLoading.value) return
  
  isLoading.value = true
  clearMessages()
  
  try {
    const response = await apis.mcpRemove({ server_url: serverUrl })
    servers.value = response.servers
    showSuccess(response.message)
  } catch (error) {
    console.error('Failed to remove MCP server:', error)
    showError('Failed to remove server. Please try again.')
  } finally {
    isLoading.value = false
  }
}

onMounted(loadServers)
</script>
