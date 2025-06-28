<script setup lang="ts">
import { useEventListener } from '@vueuse/core';
import * as echarts from 'echarts';
import { computed, onMounted, onUnmounted, ref, watch, watchEffect } from 'vue';
import { usePreviewHtml } from '../composables/usePreviewHtml';
import { echartsCategories, graphEdges, graphNodes } from '../graph';
import apis from '../rpc';
import { status } from '../states';
import KnowledgeGraph from './KnowledgeGraph.vue';

const container = ref<HTMLDivElement | null>(null);
let myChart: echarts.ECharts | null = null;

// Context menu state
const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  nodeId: null as string | null
});

// Confirmation dialog state
const confirmDialog = ref({
  visible: false,
  nodeId: null as string | null,
  nodeName: ''
});

// Focus state
const focusedNodeId = ref<string | null>(null);
const focusedNodeType = ref<string | null>(null);
const focusedNodeKgStatusOriginal = computed(() => {
  const id = focusedNodeId.value;
  if (!id) return;
  return status.value.knowledge_graph?.[id]
})
const focusedNodeKgStatus = ref(focusedNodeKgStatusOriginal.value);
watch([
  focusedNodeKgStatusOriginal,
  focusedNodeId,
], () => focusedNodeKgStatus.value = focusedNodeKgStatusOriginal.value);

// Drag and drop state
const dragOver = ref(false);
const uploading = ref(false);
const uploadError = ref<string | null>(null);

function updateChart() {
  if (!myChart) return;

  if (graphNodes.value.length === 0) {
    myChart.clear();
    return;
  }

  myChart.showLoading();

  const option = {
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
        edgeLength: 200,
        layoutAnimation: false,
        initLayout: 'circular' // Start with circular layout
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
  myChart.resize();
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
  
  // If no params or no data, it means clicked on empty area
  if (!params || !params.data || params.dataType !== 'node') {
    // Clicked on empty area, clear focus
    focusedNodeId.value = null;
    focusedNodeType.value = null;
    updateNodeFocus(null);
    return;
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
  const nodeId = contextMenu.value.nodeId || focusedNodeId.value;
  if (!nodeId) return;

  // Show confirmation dialog
  confirmDialog.value = {
    visible: true,
    nodeId: nodeId,
    nodeName: nodeId.split('/').pop() || nodeId
  };

  // Hide context menu
  contextMenu.value.visible = false;
}

function confirmDelete() {
  if (!confirmDialog.value.nodeId) return;

  apis.fsDelete({ path: confirmDialog.value.nodeId })

  // Clear focus if the deleted node was focused
  if (focusedNodeId.value === confirmDialog.value.nodeId) {
    focusedNodeId.value = null;
    updateNodeFocus(null);
  }

  // Hide dialog
  confirmDialog.value.visible = false;
}

function cancelDelete() {
  confirmDialog.value.visible = false;
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

    // Add click listener to handle empty area clicks
    myChart.getZr().on('click', (event: any) => {
      // If the click target is not a graph element, clear focus
      if (!event.target) {
        contextMenu.value.visible = false;
        focusedNodeId.value = null;
        focusedNodeType.value = null;
        updateNodeFocus(null);
      }
    });

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

onUnmounted(() => {
  myChart?.dispose()
})

const previewHtml = usePreviewHtml(focusedNodeId);
const kgPath = computed(() => focusedNodeKgStatus.value?.status === 'done' ? focusedNodeId.value : null)
const largeKg = ref(false)
watch(kgPath, () => largeKg.value = false);

async function kgAction() {
  const id = focusedNodeId.value;
  if (!id) return;
  const s = focusedNodeKgStatus.value?.status;
  if (s === 'done') {
    largeKg.value = true;
  }
  else if (s !== 'in_progress') {
    focusedNodeKgStatus.value = {
      status: 'in_progress',
      progress: 0,
    }
    // Trigger knowledge graph generation
    await apis.kgSpawn({ path: id });
  }
}

// Drag and drop handlers
function handleDragOver(event: DragEvent) {
  event.preventDefault();
  event.stopPropagation();
  dragOver.value = true;
}

function handleDragLeave(event: DragEvent) {
  event.preventDefault();
  event.stopPropagation();
  dragOver.value = false;
}

function handleDrop(event: DragEvent) {
  event.preventDefault();
  event.stopPropagation();
  dragOver.value = false;

  const files = event.dataTransfer?.files;
  if (!files || files.length === 0 || !focusedNodeId.value) return;

  uploadFiles(Array.from(files));
}

async function uploadFiles(files: File[]) {
  if (!focusedNodeId.value) return;

  uploading.value = true;
  uploadError.value = null; // Clear previous errors

  try {
    const formData = new FormData();
    
    // Add all files to the same FormData
    files.forEach(file => {
      formData.append('files', file);
    });
    
    // Add the directory path
    formData.append('path', focusedNodeId.value);

    // Upload all files in a single request
    const response = await fetch(`${import.meta.env.VITE_API_SERVER_URL}/fs/upload`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Upload failed: ${errorText}`);
    }

    const result = await response.json();
    console.log(`Successfully uploaded ${result.total_files} file(s)`);
  } catch (error) {
    console.error('Upload failed:', error);
    uploadError.value = error instanceof Error ? error.message : 'Upload failed';
  } finally {
    uploading.value = false;
  }
}

function handleFileInput(event: Event) {
  const input = event.target as HTMLInputElement;
  if (input.files) {
    uploadFiles(Array.from(input.files));
  }
  // Clear the input so the same file can be selected again
  (event.target as HTMLInputElement).value = '';
}
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
          <button v-if="focusedNodeType !== 'directory'" @click="downloadNode"
            class="p-1 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors" title="Download">
            <div class="i-carbon-download w-4 h-4"></div>
          </button>
          <button @click="deleteNode"
            class="p-1 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors" title="Delete">
            <div class="i-carbon-trash-can w-4 h-4"></div>
          </button>
        </div>
      </div>
      <div v-if="previewHtml" v-html="previewHtml" class="border-0 w-full children:break-words children:text-pretty flex-grow my-2 border-t pt-4 max-h-120 overflow-y-auto" />

      <!-- Drag and Drop Upload Area for Directories -->
      <div v-if="focusedNodeType === 'directory'" class="mt-2 mb-2" @dragover="handleDragOver"
        @dragleave="handleDragLeave" @drop="handleDrop">
        <div class="border-1 rounded-lg p-6 text-center transition-all duration-200 cursor-pointer"
          :class="{
            'border-blue-300 bg-blue-50': dragOver && !uploadError,
            'border-gray-300 bg-gray-50 hover:border-gray-400 hover:bg-gray-100': !dragOver && !uploading && !uploadError,
            'border-orange-300 bg-orange-50': uploading,
            'border-red-300 bg-red-50': uploadError
          }">
          <div class="flex flex-col items-center gap-2">
            <div v-if="uploading" class="i-mdi-loading w-6 h-6 text-orange-500 animate-spin"></div>
            <div v-else-if="uploadError" class="i-carbon-warning-filled w-6 h-6 text-red-500"></div>
            <div v-else-if="dragOver" class="i-carbon-cloud-upload w-6 h-6 text-blue-500"></div>
            <div v-else class="i-carbon-document-add w-6 h-6 text-gray-400"></div>

            <label for="file-upload" class="text-sm">
              <div v-if="uploading" class="text-orange-600 font-medium">Uploading files...</div>
              <div v-else-if="uploadError" class="text-red-600 font-medium">Upload failed</div>
              <div v-else-if="dragOver" class="text-blue-600 font-medium">Drop files here</div>
              <div v-else>
                <div class="text-gray-600 font-medium">Drag files here to upload</div>
                <div class="text-xs text-gray-500 mt-1">
                  or click to browse
                </div>
              </div>
            </label>
            
            <!-- Error message -->
            <div v-if="uploadError" class="text-xs text-red-500 mt-1 max-w-full break-words">
              {{ uploadError }}
            </div>
          </div>
          <input id="file-upload" type="file" multiple class="hidden" @change="handleFileInput" />
        </div>
      </div>

      <div>
        <button
          class="w-full px-3 py-2 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors mt-2 relative"
          :class="{
            'bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200': focusedNodeKgStatus?.status === 'done',
            'bg-yellow-50 hover:bg-yellow-100 text-yellow-700 border border-yellow-200': focusedNodeKgStatus?.status === 'in_progress',
            'bg-red-50 hover:bg-red-100 text-red-700 border border-red-200': focusedNodeKgStatus?.status === 'error'
          }" @click="kgAction">

          <div flex items-center gap-2 justify-center>
            <!-- Status indicator icon -->
            <div v-if="focusedNodeKgStatus?.status === 'done'" class="i-carbon-checkmark-filled w-4 h-4 text-green-600">
            </div>
            <div v-else-if="focusedNodeKgStatus?.status === 'in_progress'"
              class="i-mdi-loading w-4 h-4 text-yellow-600 animate-spin"></div>
            <div v-else-if="focusedNodeKgStatus?.status === 'error'"
              class="i-carbon-warning-filled w-4 h-4 text-red-600"></div>
            <div v-else class="i-carbon-chart-relationship w-4 h-4"></div>

            <span>Knowledge Graph</span>

            <!-- Status text -->
            <span class="text-xs opacity-75 ml-auto">
              {{ focusedNodeKgStatus?.status === 'done' ? 'Ready' :
                focusedNodeKgStatus?.status === 'in_progress' ? 'Processing...' :
                  focusedNodeKgStatus?.status === 'error' ? 'Failed' : 'Generate' }}
            </span>
          </div>
          <pre v-if="focusedNodeKgStatus?.status === 'error'" v-text="focusedNodeKgStatus.message" text-red-600 text-sm
            text-left mt-1 />

          <div v-if="kgPath" mt-2 mb-1 h-40>
            <KnowledgeGraph :path="kgPath" />
          </div>
          <Teleport to="body" v-if="kgPath && largeKg">
            <div fixed inset-0 z-40 backdrop-blur-sm flex items-center justify-center p-20 @click="largeKg = false">
              <KnowledgeGraph :path="kgPath" show-header @click.prevent="(event) => event.stopPropagation()"
                @close="largeKg = false" />
            </div>
          </Teleport>
        </button>
      </div>
    </div>

    <!-- Confirmation Dialog -->
    <div v-if="confirmDialog.visible"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
      <div class="bg-white rounded-lg shadow-xl border border-gray-200 p-6 max-w-md w-full mx-4">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center">
            <div class="i-carbon-warning w-5 h-5 text-red-600"></div>
          </div>
          <div>
            <h3 class="text-lg font-semibold text-gray-900">Delete File</h3>
            <p class="text-sm text-gray-600">This action cannot be undone.</p>
          </div>
        </div>

        <div class="mb-6">
          <p class="text-sm text-gray-700">
            Are you sure you want to delete
            <span class="font-mono bg-gray-100 px-1 py-0.5 rounded text-xs">{{ confirmDialog.nodeName }}</span>?
          </p>
        </div>

        <div class="flex gap-3 justify-end">
          <button @click="cancelDelete"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors">
            Cancel
          </button>
          <button @click="confirmDelete"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors">
            Delete
          </button>
        </div>
      </div>
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