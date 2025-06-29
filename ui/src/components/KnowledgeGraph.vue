<script setup lang="ts">
import { useEventListener } from '@vueuse/core';
import * as echarts from 'echarts';
import { onMounted, ref, shallowRef, watch } from 'vue';
import apis from '../rpc';
import { status } from '../states';

const props = defineProps<{
  path: string,
  showHeader?: boolean,
}>()

// Add emit for close event
const emit = defineEmits<{
  close: []
}>()

const data = shallowRef<{ subject: string; predicate: string; object: string }[] | null>(null)

let lastWork = NaN
watch(() => {
  const s = status.value.knowledge_graph?.[props.path]
  return [props.path, s?.status === 'done' ? s.done_at : false] as const
}, async ([path, done_at]) => {
  console.log(path, done_at)
  if (!done_at) return
  try {
    const myWork = lastWork = Date.now()
    const response = await apis.kgContent({ path })
    if (myWork !== lastWork) return // Ignore if a newer request has been made
    data.value = response
  } catch (error) {
    console.error('Error fetching knowledge graph data:', error)
    data.value = null
  }
}, { immediate: true })


const chartContainer = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const initChart = async () => {
  if (!chartContainer.value) return

  chart = echarts.init(chartContainer.value)
  updateChart()

  const doResize = () => {
    if (chart) {
      chart.resize()
    }
  }

  useEventListener(window, 'resize', doResize)
  setTimeout(doResize, 50)
  setTimeout(doResize, 200)
  setTimeout(doResize, 600)
  setTimeout(doResize, 1000)
}

const updateChart = () => {
  if (!chart || !data.value) return

  // 提取所有唯一的节点
  const nodeSet = new Set<string>()
  const links: any[] = []

  data.value.forEach(triple => {
    nodeSet.add(triple.subject)
    nodeSet.add(triple.object)

    links.push({
      source: triple.subject,
      target: triple.object,
      label: {
        show: true,
        formatter: triple.predicate,
        fontSize: 16,
        color: '#000',
      },
      lineStyle: {
        color: '#666',
        width: 2,
      },
      symbol: ['none', 'arrow'],
      symbolSize: [0, 15]
    })
  })

  const nodes = Array.from(nodeSet).map(name => ({
    id: name,
    name: name,
    symbolSize: 30,
    itemStyle: {
      color: '#4dabf7'
    },
    label: {
      show: true,
      fontSize: 16
    }
  }))

  const option = {
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: links,
      roam: true,
      label: {
        show: true,
        position: 'right'
      },
      force: {
        repulsion: 1000,
        gravity: 0.1,
        edgeLength: 150,
        layoutAnimation: true
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: {
          width: 3
        },
        label: {
          show: true
        }
      },
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [0, 15]
    }]
  }

  chart.setOption(option)
  chart.resize()
}

// Add refresh functionality
const refreshData = async () => {
  if (!props.path) return
  try {
    const myWork = lastWork = Date.now()
    const response = await apis.kgContent({ path: props.path })
    if (myWork !== lastWork) return
    data.value = response
  } catch (error) {
    console.error('Error refreshing knowledge graph data:', error)
    data.value = null
  }
}

onMounted(() => {
  initChart()
})

watch(data, () => {
  updateChart()
})
</script>

<template>
  <div class="w-full h-full flex flex-col bg-white rounded-lg shadow-lg overflow-hidden">
    <!-- Header -->
    <div v-if="showHeader" class="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
      <div class="flex items-center gap-2 flex-1 min-w-0">
        <i class="i-carbon-chart-relationship w-5 h-5 flex-shrink-0"></i>
        <span class="text-sm font-medium text-gray-700">Knowledge Graph</span>
        <span class="text-xs text-gray-500">-</span>
        <span class="text-xs text-gray-600 truncate" :title="props.path">{{ props.path }}</span>
      </div>
      <div flex-grow />
      <div class="flex items-center gap-2">
        <button @click="refreshData" class="p-1.5 hover:bg-gray-200 rounded-md transition-colors" title="Refresh">
          <i class="i-mdi-refresh block w-6 h-6 text-gray-500"></i>
        </button>
        <button @click="emit('close')" class="p-1.5 hover:bg-gray-200 rounded-md transition-colors" title="Close">
          <i class="i-mdi-close block w-6 h-6 text-gray-500"></i>
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 min-h-0 relative">
      <div v-show="data" ref="chartContainer" class="absolute inset-0 w-full h-full"></div>
      <div v-if="!data" class="absolute inset-0 flex items-center justify-center bg-gray-50">
        <div class="flex flex-col items-center gap-3 text-gray-500">
          <i class="i-mdi-loading animate-spin w-8 h-8 text-blue-500"></i>
          <span class="text-sm">Loading knowledge graph...</span>
        </div>
      </div>
      <div v-else-if="data && data.length === 0" class="absolute inset-0 flex items-center justify-center bg-gray-50">
        <div class="flex flex-col items-center gap-3 text-gray-500">
          <i class="i-carbon-chart-relationship w-8 h-8"></i>
          <span class="text-sm">Empty</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.knowledge-graph {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
</style>
