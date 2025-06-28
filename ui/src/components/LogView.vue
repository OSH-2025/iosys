<template>
  <div class="p-6 max-w-full flex flex-col h-full">

    <!-- Search -->
    <div class="mb-4 flex items-center gap-4">
      <i class="i-carbon-search text-gray-500 mr--2 ml-2 text-2xl"></i>

      <input v-model="searchQuery" type="text" placeholder="Search logs..."
        class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500" />

      <button @click="refreshLogs" :disabled="loading"
        class="px-3 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center">

        {{ loading ? 'Loading...' : 'Refresh' }}
      </button>
    </div>

    <!-- Table -->
    <div class="border border-gray-200 rounded-lg h-0 flex-grow flex flex-col">
      <!-- Fixed Header -->
      <div class="bg-gray-50 border-b border-gray-200">
        <table class="w-full text-sm">
          <thead>
            <tr>
              <th class="px-4 py-3 text-left font-medium text-gray-900 w-38">Timestamp</th>
              <th class="px-4 py-3 text-left font-medium text-gray-900 w-20">Level</th>
              <th class="px-4 py-3 text-left font-medium text-gray-900 w-24">Name</th>
              <th class="px-4 py-3 text-left font-medium text-gray-900">Message</th>
            </tr>
          </thead>
        </table>
      </div>
      
      <!-- Scrollable Body -->
      <div class="flex-1 overflow-y-auto">
        <table class="w-full text-sm">
          <tbody class="divide-y divide-gray-200">
            <tr v-if="loading && logs.length === 0">
              <td colspan="4" class="px-4 py-8 text-center text-gray-500">
                <div
                  class="inline-block w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin mr-2">
                </div>
                Loading logs...
              </td>
            </tr>
            <tr v-else-if="filteredLogs.length === 0 && !loading">
              <td colspan="4" class="px-4 py-8 text-center text-gray-500">
                {{ logs.length === 0 ? 'No logs found' : 'No logs match your search' }}
              </td>
            </tr>
            <tr v-for="log in filteredLogs" :key="`${log.timestamp}-${log.name}-${log.message}`" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-gray-600 font-mono text-xs w-38">
                {{ formatTimestamp(log.timestamp) }}
              </td>
              <td class="px-4 py-3 w-20">
                <span :class="getLevelClass(log.level)" class="px-2 py-1 text-xs font-medium rounded-full">
                  {{ log.level.toUpperCase() }}
                </span>
              </td>
              <td class="px-4 py-3 text-gray-900 font-medium w-24">
                {{ log.name }}
              </td>
              <td class="px-4 py-3 text-gray-700 break-words">
                {{ log.message }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Footer info -->
    <div class="mt-4 text-xs text-gray-500 text-center">
      {{ filteredLogs.length }} of {{ logs.length }} logs
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import apis, { type ApiResponse } from '../rpc'

type LogEntry = ApiResponse<'getLogs'>[0]

const logs = ref<LogEntry[]>([])
const searchQuery = ref('')
const loading = ref(false)

const filteredLogs = computed(() => {
  if (!searchQuery.value) return logs.value

  const query = searchQuery.value.toLowerCase()
  return logs.value.filter(log =>
    log.message.toLowerCase().includes(query) ||
    log.name.toLowerCase().includes(query) ||
    log.level.toLowerCase().includes(query)
  )
})

const refreshLogs = async () => {
  loading.value = true
  try {
    logs.value = await apis.getLogs({})
  } catch (error) {
    console.error('Failed to load logs:', error)
  } finally {
    loading.value = false
  }
}

const formatTimestamp = (timestamp: string) => {
  return new Date(timestamp).toLocaleString('en-US', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const getLevelClass = (level: string) => {
  const levelMap = {
    error: 'bg-red-100 text-red-800',
    warn: 'bg-yellow-100 text-yellow-800',
    info: 'bg-blue-100 text-blue-800',
    debug: 'bg-gray-100 text-gray-800'
  }
  return levelMap[level.toLowerCase() as keyof typeof levelMap] || 'bg-gray-100 text-gray-800'
}

onMounted(() => {
  refreshLogs()
})
</script>
