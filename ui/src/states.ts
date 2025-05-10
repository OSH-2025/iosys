import { reactive, ref, shallowRef } from "vue";
import { Network, DataSet } from 'vis-network/standalone/esm/vis-network';
import type { Node, Edge, Options } from 'vis-network/standalone/esm/vis-network';

interface Message {
  fromUser: boolean;
  content: string;
}

export const messages = reactive<Message[]>([
  {
    fromUser: false,
    content: "### Hello!\nHow can I assist you today?",
  },
  {
    fromUser: true,
    content: "I need help with my order.",
  },
  {
    fromUser: false,
    content: "Sure! Can you please provide your order number?",
  },
  {
    fromUser: true,
    content: "My order number is 12345.",
  },
  {
    fromUser: false,
    content: "Thank you! Let me check that for you.",
  },
]);

export const errorMessage = ref<string | null>(null);

export const graphNodes = shallowRef<Node[]>([
  { id: 1, label: 'Document 1', group: 'document' },
  { id: 2, label: 'Chunk 1.1', group: 'chunk' },
  { id: 3, label: 'Chunk 1.2', group: 'chunk' },
  { id: 4, label: 'Query', group: 'query' },
  { id: 5, label: 'Answer', group: 'answer' },
  { id: 6, label: 'Document 2', group: 'document' },
  { id: 7, label: 'Chunk 2.1', group: 'chunk' },
]);
export const graphEdges = shallowRef<Edge[]>([
  { from: 1, to: 2 }, // Document 1 to Chunk 1.1
  { from: 1, to: 3 }, // Document 1 to Chunk 1.2
  { from: 4, to: 2, label: 'retrieved' }, // Query retrieves Chunk 1.1
  { from: 4, to: 7, label: 'retrieved' }, // Query retrieves Chunk 2.1
  { from: 2, to: 5, label: 'generates' }, // Chunk 1.1 generates Answer
  { from: 7, to: 5, label: 'generates' }, // Chunk 2.1 generates Answer
  { from: 6, to: 7 }, // Document 2 to Chunk 2.1
]);
