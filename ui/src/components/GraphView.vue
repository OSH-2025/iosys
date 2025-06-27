<script setup lang="ts">
import { onMounted, ref, watchEffect } from 'vue';
import * as echarts from 'echarts';
import { graphNodes, graphEdges, echartsCategories } from '../graph';
import { useEventListener } from '@vueuse/core';
import { previewFile } from '../states'

const container = ref<HTMLDivElement | null>(null);
let myChart: echarts.ECharts | null = null;

function updateChart() {
  if (!myChart) return;

  if (graphNodes.value.length === 0) {
    myChart.clear();
    return;
  }

  myChart.showLoading();

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          return `${params.data.name}`;
        } else {
          return `${params.data.label?.formatter || ''}`;
        }
      }
    },
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
        formatter: '{b}'
      },
      lineStyle: {
        color: 'source',
        curveness: 0.1,
        width: 2
      },
      emphasis: {
        focus: 'adjacency',
        scale: 1.2,
        lineStyle: {
          width: 4
        }
      }
    }]
  } satisfies echarts.EChartsCoreOption;

  myChart.setOption(option, true);
  myChart.hideLoading();
};

// Handle node click events
function handleNodeClick(params: any) {
  if (!myChart || !params.data) return;

  if (params.dataType === 'node') {
    if (params.data.category === 'file') {
      previewFile.value = params.data.id;
    } else {
      previewFile.value = null;
    }
  }
}

onMounted(() => {
  if (container.value) {
    myChart = echarts.init(container.value);

    myChart.on('click', handleNodeClick);

    useEventListener(window, 'resize', () => {
      if (myChart) {
        myChart.resize();
      }
    });

    watchEffect(updateChart);
  } else {
    console.error('Container is not available');
  }
});
</script>

<template>
  <div relative w-full h-full>
    <div ref="container" style="width: 100%; height: 100%;"></div>
    <div v-if="graphNodes.length === 0"
      class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-gray-500">
      No nodes available
    </div>
  </div>
</template>