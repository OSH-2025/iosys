<script setup lang="ts">
import { computed, onMounted, ref, watchEffect } from 'vue';
import * as echarts from 'echarts';
import { graphNodes, graphEdges, echartsCategories } from '../graph';
import { useEventListener } from '@vueuse/core';
import { previewFile } from '../states'
import { usePreviewHtml } from '../composables/usePreviewHtml';

const container = ref<HTMLDivElement | null>(null);
let myChart: echarts.ECharts | null = null;

// Context menu state
const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  nodeId: null as string | null
});

// Focus state
const focusedNodeId = ref<string | null>(null);
const focusedNodeType = ref<string | null>(null);

function updateChart() {
  if (!myChart) return;

  if (graphNodes.value.length === 0) {
    myChart.clear();
    return;
  }

  myChart.showLoading();

  const option = {
    legend: [{
      data: echartsCategories.map(cat => cat.name),
      orient: 'vertical',
      left: 'left',
      top: 'top'
    }],
    animationDuration: 1500,
    animationEasingUpdate: 'quinticInOut',
    series: [{
      type: 'graph',
      layout: 'force',
      nodes: graphNodes.value,
      edges: graphEdges.value,
      categories: echartsCategories,
      roam: true,
      force: {
        repulsion: 1000,
        gravity: 0.1,
        edgeLength: 200,
        layoutAnimation: true
      },
      label: {
        show: true,
        position: 'right',
        formatter: '{b}',
        fontSize: 12
      },
      lineStyle: {
        color: 'source',
        curveness: 0.1,
        width: 2
      },
      emphasis: {
        scale: 1.3,
        label: {
          fontSize: 14,
          fontWeight: 'bold',
          color: '#000',
          padding: [2, 4]
        },
        lineStyle: {
          width: 6,
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.3)'
        },
        itemStyle: {
          shadowBlur: 15,
          shadowColor: 'rgba(0, 0, 0, 0.4)',
          borderWidth: 3,
          borderColor: '#fff'
        }
      }
    }]
  } satisfies echarts.EChartsCoreOption;

  myChart.setOption(option, true);
  myChart.hideLoading();
};

// Function to update node focus without re-rendering the entire chart
function updateNodeFocus(nodeId: string | null) {
  if (!myChart) return;

  // Clear previous highlight
  myChart.dispatchAction({
    type: 'downplay',
    seriesIndex: 0
  });

  if (nodeId) {
    // Find the node index
    // @ts-expect-error
    const nodeIndex = graphNodes.value.findIndex(node => node.id === nodeId);
    if (nodeIndex !== -1) {
      // Highlight the focused node
      myChart.dispatchAction({
        type: 'highlight',
        seriesIndex: 0,
        dataIndex: nodeIndex
      });
    }
  }
}

// Handle node click events
function handleNodeClick(params: any) {
  // Hide context menu on regular click
  contextMenu.value.visible = false;

  if (!myChart) return;
  if (!params.data) {
    // Clicked on empty area, clear focus
    focusedNodeId.value = null;
    updateNodeFocus(null);
    contextMenu.value.visible = false;
  }

  if (params.dataType === 'node') {
    // Set focus to clicked node
    focusedNodeId.value = params.data.id;
    focusedNodeType.value = params.data.category || null;
    updateNodeFocus(params.data.id);
  }
}

// Handle right-click events
function handleContextMenu(params: any) {
  if (!params.data || params.dataType !== 'node') return;

  const event = params.event?.event as MouseEvent;
  if (!event) return;

  event.preventDefault();

  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    nodeId: params.data.id
  };
}

// Delete node and related edges
function deleteNode() {
  
}

function downloadNode(ev: Event) {
  if (focusedNodeId.value) {
    ev.stopPropagation();
    const link = document.createElement('a');
    link.download = focusedNodeId.value.split('/').pop() || 'download';
    link.href = `${import.meta.env.VITE_API_SERVER_URL}/raw?path=${encodeURIComponent(focusedNodeId.value)}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

// Hide context menu when clicking elsewhere
function hideContextMenu() {
  contextMenu.value.visible = false;
}

onMounted(() => {
  if (container.value) {
    myChart = echarts.init(container.value);

    myChart.on('click', handleNodeClick);
    myChart.on('contextmenu', handleContextMenu);

    useEventListener(window, 'resize', () => {
      if (myChart) {
        myChart.resize();
      }
    });

    useEventListener(window, 'click', hideContextMenu);

    watchEffect(updateChart);
  } else {
    console.error('Container is not available');
  }
});

const previewHtml = usePreviewHtml(computed(() => focusedNodeType.value === 'file' ? focusedNodeId.value : null));
</script>

<template>
  <div relative w-full h-full>
    <div ref="container" style="width: 100%; height: 100%;"></div>
    <div v-if="graphNodes.length === 0"
      class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-gray-500">
      No nodes available
    </div>

    <!-- Focused Node Display -->
    <div v-if="focusedNodeId"
      class="absolute top-4 right-4 bg-white/90 backdrop-blur-sm border border-gray-200 rounded-lg px-3 py-2 shadow-lg w-80 flex flex-col overflow-y-auto max-h-180">
      <div class="flex items-center justify-between">
        <div class="text-lg text-gray-800 font-mono">{{ focusedNodeId }}</div>
        <div class="flex items-center gap-2">
          <button
            v-if="focusedNodeType === 'file'"
            @click="downloadNode" 
            class="p-1 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
            title="Download">
            <div class="i-carbon-download w-4 h-4"></div>
          </button>
          <button @click="deleteNode" 
            class="p-1 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
            title="Delete">
            <div class="i-carbon-trash-can w-4 h-4"></div>
          </button>
        </div>
      </div>
      <div v-if="previewHtml" v-html="previewHtml" class="border-0 w-full flex-grow my-2 border-t pt-2" />
    </div>

    <!-- Custom Context Menu -->
    <div v-if="contextMenu.visible" :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
      class="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-32" @click.stop>
      <button @click="deleteNode"
        class="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 transition-colors">
        <div class="i-carbon-trash-can w-4 h-4"></div>
        Delete
      </button>
    </div>
  </div>
</template>