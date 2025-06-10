<template>
  <article v-html="renderedContent" class="markdown-body"></article>
</template>

<script lang="ts">
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt({
  html: true,
  breaks: true,
  linkify: true,
});
</script>

<script setup lang="ts">
import "github-markdown-css/github-markdown-light.css";
import { computed } from 'vue';

const props = defineProps<{
  content: string
}>();

const renderedContent = computed(() => md.render(props.content || ''));
</script>

<style scoped>
.markdown-body {
  background-color: unset !important;
  color: unset !important;
}
</style>
