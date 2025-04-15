<template>
  <article v-html="renderedContent" class="markdown-body"></article>
</template>

<script setup lang="ts">
import "github-markdown-css/github-markdown-light.css"
import { ref, watchEffect } from 'vue';
import MarkdownIt from 'markdown-it';

const props = defineProps<{
  content: string
}>();

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
});

const renderedContent = ref('');

watchEffect(() => {
  renderedContent.value = md.render(props.content || '');
});
</script>

<style scoped>
.markdown-body {
  background-color: unset !important;
  color: unset !important;
}
</style>
