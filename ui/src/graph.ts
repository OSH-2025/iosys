import { ref, shallowRef, computed } from 'vue';
import rpc from "./rpc";
import { status } from './states';
import { whenever } from '@vueuse/core';
import type * as echarts from 'echarts';

export interface RawGraph {
  nodes: Record<string, {
    label: string;
    embedding: unknown | null;
    properties: Record<string, unknown>;
    name: string;
  }>,
  relations: Record<string, {
    label: string;
    source_id: string;
    target_id: string;
    properties: Record<string, unknown>;
  }>,
  triplets: [string, string, string][],
  revision: number,
}

const currentRevision = ref(-1);
export const graphNodes = shallowRef<echarts.GraphSeriesOption["nodes"] & {}>([]);
export const graphEdges = shallowRef<echarts.GraphSeriesOption["edges"] & {}>([]);

export const echartsCategories = [
  { name: 'root', itemStyle: { color: '#2196F3' } },
  { name: 'file', itemStyle: { color: '#FFC107' } },
  { name: 'directory', itemStyle: { color: '#4CAF50' } },
];

whenever(
  () => currentRevision.value < (status.value.graph_revision || 0),
  async () => {
    const graph = await rpc.graph({});
    if (graph.revision < (status.value.graph_revision || 0) || graph.revision < currentRevision.value)
      return;
    currentRevision.value = graph.revision;
    graphNodes.value = Object.entries(graph.nodes)
      .filter(([_, node]) => node.label !== 'event')
      .map(([id, node]) => ({
        id,
        name: node.name.split('/').pop() || node.name,
        category: node.name === '/' ? 'root' : node.label,
        symbolSize: 30,
        label: {
          show: true
        },
        // // @ts-expect-error
        // tooltip: {
        //   formatter: (params: any) => {
        //     const node = graph.nodes[params.data.id];
        //     return `
        //       <strong>${node.name}</strong><br>
        //     `;
        //   }
        // }
      } satisfies (echarts.GraphSeriesOption["nodes"] & {})[number]));
    graphEdges.value = Object.entries(graph.relations)
      .filter(([_, relation]) => graph.nodes[relation.source_id].label !== 'event')
      .map(([_id, relation]) => ({
        source: relation.source_id,
        target: relation.target_id,
        label: {
          show: true,
          formatter: relation.label
        },
      } satisfies (echarts.GraphSeriesOption["edges"] & {})[number]));
  },
  { immediate: true }
)