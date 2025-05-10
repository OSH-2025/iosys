<script setup lang="ts">
import { ref, watch, watchEffect } from 'vue';
import { previewFile } from '../states';
import rpc from '../rpc';

const url = ref<string | null>(null);
let processingFile: string | null = null;
watch(
  previewFile,
  async () => {
    processingFile = previewFile.value;
    if (processingFile) {
      const response = await rpc.preview({ id: processingFile });
      if (processingFile === previewFile.value)
        url.value = response.url;
    }
  }, { immediate: true });

function close(ev: Event) {
  if (previewFile.value) {
    ev.stopPropagation();
    previewFile.value = null;
  }
}
</script>

<template>
  <!-- <div :class="previewFile ? '' : 'op-0 pointer-events-none'" class="bg-black/5 absolute inset-0" @click="close"/> -->
  <div :class="previewFile ? '' : 'translate-x-100%'"
    class="absolute transition-transform duration-300 ease-in-out right-0 top-0 bottom-0 bg-white shadow-xl px-8 py-6"
    style="width: min(800px, 40vw);">
    <button i-carbon-close-large text-2xl float-right hover:op-60 @click="close"/>
    <h2 class="text-xl font-semibold mb-4">File Preview</h2>
    <div v-if="previewFile">
      <img v-if="url" :src="url" border="0" width="100%" height="500px"></img>
      <p v-else op-80>
        Loading {{ previewFile }}...
      </p>
    </div>
  </div>
</template>
