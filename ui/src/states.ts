import { reactive, ref } from "vue";
import { useIntervalFn } from '@vueuse/core';
import rpc, { ApiResponse } from './rpc';

interface Message {
  fromUser: boolean;
  content: string;
}

export const messages = reactive<Message[]>([
  {
    fromUser: false,
    content: "### Hello!\nHow can I assist you today?",
  },
]);

export const errorMessage = ref<string | null>(null);

export const previewFile = ref<string | null>(null);

export const status = ref<Partial<ApiResponse<"status">>>({});

useIntervalFn(
  async () => {
    try {
      status.value = await rpc.status({});
    } catch (e) {
      status.value = {
        server: 'offline',
      }
    }
  },
  10000,
  { immediate: true, immediateCallback: true }
);
