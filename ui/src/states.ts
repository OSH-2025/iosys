import { reactive, ref } from "vue";
import rpc, { ApiResponse } from './rpc';

interface Message {
  fromUser: boolean;
  content: string;
}

export const messages = reactive<Message[]>([]);
export const currentSessionId = ref<string>("");
resetMessages();

export function resetMessages() {
  messages.length = 0;
  messages.push({
    fromUser: false,
    content: "### Hello!\nHow can I assist you today?",
  });
  currentSessionId.value = Date.now().toString();
}

export const errorMessage = ref<string | null>(null);

export const previewFile = ref<string | null>(null);

export const status = ref<Partial<ApiResponse<"status">>>({});


let working = 0;

export async function refreshStatus() {
  if (working) return;
  const myWorking = working = Date.now();
  try {
    status.value = await rpc.status({});
  } catch (e) {
    status.value = {
      server: 'offline',
    }
  } finally {
    if (myWorking === working) {
      working = 0;
    }
  }
}

const intervalId = setInterval(refreshStatus, 1000);

if (import.meta.hot) {
  import.meta.hot.on('vite:beforeUpdate', () => {
    clearInterval(intervalId);
  });
}
