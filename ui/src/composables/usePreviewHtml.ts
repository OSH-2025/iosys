import { ref, Ref, watch } from "vue";
import apis from "../rpc";

export function usePreviewHtml(path: Ref<string | null>) {
  const html = ref<string | null>(null);

  watch(path, async (newPath) => {
    if (!newPath) {
      html.value = null;
      return;
    }

    try {
      html.value = await apis.preview({ path: newPath });
    } catch (error) {
      console.error("Failed to fetch preview HTML:", error);
      html.value = null;
    }
  }, { immediate: true });

  return html
}