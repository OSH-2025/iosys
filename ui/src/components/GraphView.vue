<script setup lang="ts">
import { onMounted, ref, watchEffect } from 'vue';
import { Network, DataSet } from 'vis-network/standalone/esm/vis-network';
import type { Node, Edge, Options } from 'vis-network/standalone/esm/vis-network';
import { graphEdges, graphNodes } from '../graph';

const options: Options = {
  nodes: {
    shape: 'dot',
    size: 16,
  },
  edges: {
    arrows: {
      to: { enabled: true, scaleFactor: 1 },
    },
    smooth: false,
  },
  physics: {
    forceAtlas2Based: {
      gravitationalConstant: -26,
      centralGravity: 0.005,
      springLength: 230,
      springConstant: 0.18,
    },
    maxVelocity: 146,
    solver: 'forceAtlas2Based',
    timestep: 0.35,
    stabilization: { iterations: 150 },
  },
  groups: {
    document: { color: { background: '#FFC107' }, borderWidth: 2 }, // Amber
    chunk: { color: { background: '#4CAF50' }, borderWidth: 2 },    // Green
    query: { color: { background: '#2196F3' }, borderWidth: 2 },     // Blue
    answer: { color: { background: '#9C27B0' }, borderWidth: 2 },    // Purple
  },
};

const container = ref<HTMLDivElement | null>(null);

const nodes = new DataSet<Node>(graphNodes.value);
const edges = new DataSet<Edge>(graphEdges.value);

watchEffect(() => {
  nodes.clear();
  nodes.update(graphNodes.value);
  edges.clear();
  edges.update(graphEdges.value);
});

onMounted(() => {
  if (container.value) {
    const data = { nodes, edges };
    new Network(container.value, data, options);
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