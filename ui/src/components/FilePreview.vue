<script setup lang="ts">
import { computed } from 'vue';
import { previewFile } from '../states';

const url = computed(() => {
  if (!previewFile.value) return;
  return `${import.meta.env.VITE_API_SERVER_URL}/preview?path=${encodeURIComponent(previewFile.value)}`;
});


function close(ev: Event) {
  if (previewFile.value) {
    ev.stopPropagation();
    previewFile.value = null;
  }
}

function download(ev: Event) {
  if (previewFile.value) {
    ev.stopPropagation();
    const link = document.createElement('a');
    link.download = previewFile.value.split('/').pop() || 'download';
    link.href = `${import.meta.env.VITE_API_SERVER_URL}/raw?path=${encodeURIComponent(previewFile.value)}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}
</script>

<template>
  <div :class="previewFile ? '' : 'op-0 pointer-events-none'" class="z-20 bg-white/50 absolute inset-0" @click="close"/>
  <div :class="previewFile ? '' : 'translate-x-100%'"
    class="z-20 absolute transition-transform duration-300 ease-in-out right-0 top-0 bottom-0 bg-white shadow-xl py-6 flex flex-col"
    style="width: min(800px, 40vw);">
    <h2 text-xl font-semibold mb-4 mx-8 flex items-center gap-2>
      File Preview
      <div flex-grow />
      <button i-carbon-download text-xl hover:op-60 @click="download" />
      <button i-carbon-close-large text-2xl hover:op-60 @click="close" />
    </h2>
    <div w-full flex-grow h-0 overflow-auto px-8 flex>
      <iframe v-if="url" :src="url" class="border-0 min-h-100 flex-grow">
        Your browser does not support iframes.
      </iframe>
    </div>
  </div>
</template>
