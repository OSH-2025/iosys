/// <reference types="vite/client" />

import { RawGraph } from "./graph";
import { errorMessage, refreshStatus } from "./states";

const BASE_URL = import.meta.env.VITE_API_SERVER_URL;


interface Status {
  server: string;
  rag: string;
  llm: string;
  fs: string;
  graph_revision: number;
  mcp_servers: Record<string, string | true>,
  knowledge_graph: Record<string, {
    status: 'error',
    message: string,
  } | {
    status: 'in_progress',
    progress: number,
  } | {
    status: 'done',
    done_at: number,
  }>;
}

const apis = {
  status: defineApi<{}, Status>("/status"),
  preview: defineApi<{ path: string }, string>("/preview"),
  agent: defineApi<{ command: string }, { status: string, message?: string, data: any }>("/agent/run", true),
  newHistory: defineApi<{ }, { }>("/agent/new", true),
  graph: defineApi<{}, RawGraph>("/graph"),
  mcpSync: defineApi<{ config: Record<string, any> }, {}>("/mcp/sync", true),
  mcpGetConfig: defineApi<{}, Record<string, any>>("/mcp/config"),
  getLogs: defineApi<{}, Array<{ timestamp: string, level: string, name: string, message: string }>>("/logs"),
  kgSpawn: defineApi<{ path: string }, {}>("/kg/spawn", true),
  kgContent: defineApi<{ path: string }, { subject: string, predicate: string, object: string }[]>("/kg/content"),
  fsDelete: defineApi<{ path: string }, {}>("/fs/delete", true),
};

export default apis;

export type ApiResponse<T extends keyof typeof apis> = Awaited<ReturnType<typeof apis[T]>>;

function defineApi<Request, Response>(endpoint: string, shouldRefreshStatus = false) {
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
    } finally {
      if (shouldRefreshStatus) {
        refreshStatus();
      }
    }
  };
}
