/// <reference types="vite/client" />

import { RawGraph } from "./graph";
import { errorMessage } from "./states";

const BASE_URL = import.meta.env.VITE_API_SERVER_URL;
console.log("BASE_URL", BASE_URL);

const apis = {
  status: defineApi<{}, { server: string, rag: string, llm: string, fs: string, graph_revision: number, mcp_servers: string[] }>("/status"),
  chat: defineApi<{ input: string }, { response: string }>("/chat"),
  preview: defineApi<{ id: string }, { url: string }>("/preview"),
  agent: defineApi<{ command: string }, { status: string, message?: string, data: any }>("/agent"),
  files: defineApi<{ path?: string }, { items: Array<{ name: string, path: string, type: string, size?: number }> }>("/files"),
  graph: defineApi<{}, RawGraph>("/graph"),
  mcpAdd: defineApi<{ server_url: string }, { status: string, message: string, servers: string[] }>("/mcp/add"),
  mcpRemove: defineApi<{ server_url: string }, { status: string, message: string, servers: string[] }>("/mcp/remove"),
};

export default apis;

export type ApiResponse<T extends keyof typeof apis> = Awaited<ReturnType<typeof apis[T]>>;

function defineApi<Request, Response>(endpoint: string) {
  return async (request: Request): Promise<Response> => {
    try {
      const response = await fetch(BASE_URL + endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        errorMessage.value = `Error: ${response.status} ${response.statusText}`;
        throw new Error(errorMessage.value);
      }

      return await response.json();
    } catch (error) {
      errorMessage.value = `${error}`;
      throw error;
    }
  };
}
