import { ref, shallowRef } from 'vue';
import type { Node, Edge } from 'vis-network/standalone/esm/vis-network';
import rpc from "./rpc";
import { status } from './states';
import { whenever } from '@vueuse/core';

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
export const graphNodes = shallowRef<Node[]>([]);
export const graphEdges = shallowRef<Edge[]>([]);


whenever(
  () => currentRevision.value < (status.value.graph_revision || 0),
  async () => {
    const graph = await rpc.graph({});
    if (graph.revision < (status.value.graph_revision || 0) || graph.revision < currentRevision.value)
      return;
    currentRevision.value = graph.revision;
    graphNodes.value = Object.entries(graph.nodes).map(([id, node]) => ({
      id,
      label: node.name,
      group: node.label,
    } satisfies Node));
    graphEdges.value = Object.entries(graph.relations).map(([id, relation]) => ({
      id,
      from: relation.source_id,
      to: relation.target_id,
      label: relation.label,
    } satisfies Edge));
  },
  { immediate: true }
)