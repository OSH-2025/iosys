<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Network, DataSet } from 'vis-network/standalone/esm/vis-network';
import type { Node, Edge, Options } from 'vis-network/standalone/esm/vis-network';

const container = ref<HTMLDivElement | null>(null);

// Sample RAG data
const nodes = new DataSet<Node>([
  { id: 1, label: 'Document 1', group: 'document' },
  { id: 2, label: 'Chunk 1.1', group: 'chunk' },
  { id: 3, label: 'Chunk 1.2', group: 'chunk' },
  { id: 4, label: 'Query', group: 'query' },
  { id: 5, label: 'Answer', group: 'answer' },
  { id: 6, label: 'Document 2', group: 'document' },
  { id: 7, label: 'Chunk 2.1', group: 'chunk' },
]);

const edges = new DataSet<Edge>([
  { from: 1, to: 2 }, // Document 1 to Chunk 1.1
  { from: 1, to: 3 }, // Document 1 to Chunk 1.2
  { from: 4, to: 2, label: 'retrieved' }, // Query retrieves Chunk 1.1
  { from: 4, to: 7, label: 'retrieved' }, // Query retrieves Chunk 2.1
  { from: 2, to: 5, label: 'generates' }, // Chunk 1.1 generates Answer
  { from: 7, to: 5, label: 'generates' }, // Chunk 2.1 generates Answer
  { from: 6, to: 7 }, // Document 2 to Chunk 2.1
]);

const options: Options = {
  nodes: {
    shape: 'dot',
    size: 16,
  },
  edges: {
    arrows: {
      to: { enabled: true, scaleFactor: 1 },
    },
    smooth:false,
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

onMounted(() => {
  if (container.value) {
    const data = { nodes, edges };
    new Network(container.value, data, options);
  }
});
</script>

<template>
  <div w-full h-full>
    <div ref="container" style="width: 100%; height: 100%; border: 1px solid lightgray;"></div>
  </div>
</template>