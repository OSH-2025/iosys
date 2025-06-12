<!-- filepath: d:\homework\OSH\team\ui\src\components\McpServers.vue -->
<template>
  <div class="p-6 max-w-4xl mx-auto">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900 mb-1">MCP Servers</h1>
        <p class="text-sm text-gray-600">Manage Model Context Protocol servers</p>
      </div>
      <button
        @click="showAddModal = true"
        class="inline-flex items-center px-4 py-2 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors"
      >
        <div class="i-carbon-add-large w-4 h-4 mr-2" />
        Add Server
      </button>
    </div>

    <!-- Status Overview -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="bg-white border border-gray-200 rounded-lg p-4">
        <div class="flex items-center">
          <div class="w-2 h-2 bg-green-500 rounded-full mr-3"></div>
          <span class="text-sm font-medium text-gray-900">Active Servers</span>
        </div>
        <div class="text-2xl font-bold text-gray-900 mt-2">{{ activeServersCount }}</div>
      </div>
      <div class="bg-white border border-gray-200 rounded-lg p-4">
        <div class="flex items-center">
          <div class="w-2 h-2 bg-red-500 rounded-full mr-3"></div>
          <span class="text-sm font-medium text-gray-900">Error Servers</span>
        </div>
        <div class="text-2xl font-bold text-gray-900 mt-2">{{ errorServersCount }}</div>
      </div>
      <div class="bg-white border border-gray-200 rounded-lg p-4">
        <div class="flex items-center">
          <div class="w-2 h-2 bg-blue-500 rounded-full mr-3"></div>
          <span class="text-sm font-medium text-gray-900">Total Servers</span>
        </div>
        <div class="text-2xl font-bold text-gray-900 mt-2">{{ totalServersCount }}</div>
      </div>
    </div>

    <!-- Server List -->
    <div class="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-medium text-gray-900">Server Configuration</h2>
      </div>
      
      <div v-if="loading" class="p-6 text-center">
        <div class="inline-block w-6 h-6 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin"></div>
        <p class="mt-2 text-sm text-gray-600">Loading servers...</p>
      </div>

      <div v-else-if="Object.keys(mcpServers).length === 0" class="p-6 text-center">
        <div class="text-gray-400 mb-2">
          <div class="i-carbon-bare-metal-server w-12 h-12 mx-auto" />
        </div>
        <p class="text-gray-600 mb-4">No MCP servers configured</p>
        <button
          @click="showAddModal = true"
          class="inline-flex items-center px-4 py-2 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors"
        >
          Add Your First Server
        </button>
      </div>

      <div v-else>
        <div
          v-for="(status, serverName) in mcpServers"
          :key="serverName"
          class="px-6 py-4 border-b border-gray-100 last:border-b-0 hover:bg-gray-50 transition-colors"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-4">
              <div class="flex items-center">
                <div
                  :class="[
                    'w-3 h-3 rounded-full mr-3',
                    status === true ? 'bg-green-500' : 'bg-red-500'
                  ]"
                ></div>
                <div>
                  <h3 class="font-medium text-gray-900">{{ serverName }}</h3>
                  <p class="text-sm text-gray-600">
                    {{ getServerTypeDisplay(serverName) }}
                  </p>
                </div>
              </div>
            </div>
            
            <div class="flex items-center space-x-2">
              <span
                :class="[
                  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                  status === true
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                ]"
              >
                {{ status === true ? 'Active' : 'Error' }}
              </span>
              
              <button
                @click="editServer(serverName)"
                class="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                title="Edit server"
              >
                <div class="i-carbon-edit w-4 h-4" />
              </button>
              
              <button
                @click="removeServer(serverName)"
                class="p-2 text-gray-400 hover:text-red-600 transition-colors"
                title="Remove server"
              >
                <div class="i-carbon-trash-can w-4 h-4" />
              </button>
            </div>
          </div>
          
          <!-- Error Details -->
          <div v-if="status !== true" class="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div class="flex">
              <div class="i-carbon-warning-alt w-5 h-5 text-red-400 mr-2 flex-shrink-0 mt-0.5" />
              <div>
                <h4 class="text-sm font-medium text-red-800 mb-1">Server Error</h4>
                <div class="text-sm text-red-700">
                  <div v-for="error in status" :key="error" class="mb-1">{{ error }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <div
      v-if="showAddModal || editingServer"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click="closeModal"
    >
      <div
        class="bg-white rounded-lg shadow-lg w-full max-w-md mx-4"
        @click.stop
      >
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-medium text-gray-900">
            {{ editingServer ? 'Edit Server' : 'Add New Server' }}
          </h3>
        </div>
        
        <form @submit.prevent="saveServer" class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Server Name
            </label>
            <input
              v-model="serverForm.name"
              type="text"
              required
              :disabled="!!editingServer"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="my-server"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Server Type
            </label>
            <select
              v-model="serverForm.type"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="stdio">Stdio</option>
              <option value="http">HTTP</option>
            </select>
          </div>
          
          <!-- Stdio Configuration -->
          <div v-if="serverForm.type === 'stdio'" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Command
              </label>
              <input
                v-model="serverForm.command"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="/path/to/executable"
              />
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Arguments (one per line)
              </label>
              <textarea
                v-model="argsText"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows="3"
                placeholder="--arg1&#10;--arg2"
              ></textarea>
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Environment Variables (KEY=VALUE, one per line)
              </label>
              <textarea
                v-model="envText"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows="3"
                placeholder="NODE_ENV=production&#10;API_KEY=secret"
              ></textarea>
            </div>
          </div>
          
          <!-- HTTP Configuration -->
          <div v-if="serverForm.type === 'http'">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Server URL
            </label>
            <input
              v-model="serverForm.url"
              type="url"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="http://localhost:8080"
            />
          </div>
          
          <div class="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              @click="closeModal"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="saving"
              class="px-4 py-2 text-sm font-medium text-white bg-black rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
            >
              {{ saving ? 'Saving...' : (editingServer ? 'Update' : 'Add') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted,  } from 'vue'
import apis from '../rpc'
import { status } from '../states'


// State
const loading = ref(false)
const saving = ref(false)
const mcpServers = computed(() => status.value.mcp_servers)
const currentConfig = ref<Record<string, any>>({})

// Modal state
const showAddModal = ref(false)
const editingServer = ref<string | null>(null)

// Form state
const serverForm = ref({
  name: '',
  type: 'stdio',
  command: '',
  url: '',
})

const argsText = ref('')
const envText = ref('')

// Computed
const activeServersCount = computed(() => 
  Object.values(mcpServers.value ?? {}).filter(status => status === true).length
)

const errorServersCount = computed(() => 
  Object.values(mcpServers.value ?? {}).filter(status => status !== true).length
)

const totalServersCount = computed(() => 
  Object.keys(mcpServers.value ?? {}).length
)

const loadCurrentConfig = () => {
  // In a real app, this would load from localStorage or API
  const stored = localStorage.getItem('mcpServersConfig')
  if (stored) {
    currentConfig.value = JSON.parse(stored)
  }
}

const saveCurrentConfig = () => {
  localStorage.setItem('mcpServersConfig', JSON.stringify(currentConfig.value))
}

const getServerTypeDisplay = (serverName: string) => {
  const config = currentConfig.value.mcpServers?.[serverName]
  if (!config) return 'Unknown'
  
  if (config.command) {
    return `Stdio: ${config.command}`
  } else if (config.url) {
    return `HTTP: ${config.url}`
  }
  return 'Unknown'
}

const editServer = (serverName: string) => {
  const config = currentConfig.value.mcpServers?.[serverName]
  if (!config) return
  
  editingServer.value = serverName
  serverForm.value.name = serverName
  
  if (config.command) {
    serverForm.value.type = 'stdio'
    serverForm.value.command = config.command
    argsText.value = config.args ? config.args.join('\n') : ''
    envText.value = config.env ? Object.entries(config.env).map(([k, v]) => `${k}=${v}`).join('\n') : ''
  } else if (config.url) {
    serverForm.value.type = 'http'
    serverForm.value.url = config.url
  }
}

const removeServer = async (serverName: string) => {
  if (!confirm(`Are you sure you want to remove server "${serverName}"?`)) {
    return
  }
  
  // Remove from config
  if (currentConfig.value.mcpServers) {
    delete currentConfig.value.mcpServers[serverName]
  }
  
  await syncConfig()
}

const closeModal = () => {
  showAddModal.value = false
  editingServer.value = null
  resetForm()
}

const resetForm = () => {
  serverForm.value = {
    name: '',
    type: 'stdio',
    command: '',
    url: '',
  }
  argsText.value = ''
  envText.value = ''
}

const saveServer = async () => {
  saving.value = true
  
  try {
    // Initialize config if needed
    if (!currentConfig.value.mcpServers) {
      currentConfig.value.mcpServers = {}
    }
    
    // Build server config
    const serverConfig: any = {}
    
    if (serverForm.value.type === 'stdio') {
      serverConfig.command = serverForm.value.command
      
      if (argsText.value.trim()) {
        serverConfig.args = argsText.value.trim().split('\n').filter(arg => arg.trim())
      }
      
      if (envText.value.trim()) {
        serverConfig.env = {}
        envText.value.trim().split('\n').forEach(line => {
          const [key, ...valueParts] = line.split('=')
          if (key && valueParts.length > 0) {
            serverConfig.env[key.trim()] = valueParts.join('=').trim()
          }
        })
      }
    } else if (serverForm.value.type === 'http') {
      serverConfig.url = serverForm.value.url
    }
    
    // Add to config
    currentConfig.value.mcpServers[serverForm.value.name] = serverConfig
    
    await syncConfig()
    closeModal()
  } catch (error) {
    console.error('Failed to save server:', error)
    alert('Failed to save server configuration')
  } finally {
    saving.value = false
  }
}

const syncConfig = async () => {
  try {
    await apis.mcpSync({ config: currentConfig.value })
    saveCurrentConfig()
  } catch (error) {
    console.error('Failed to sync MCP config:', error)
    alert('Failed to sync server configuration')
  }
}

// Initialize
onMounted(async () => {
  loadCurrentConfig()
})
</script>