---
aside: false
---

# 中期报告

<a :href="url" text-xl my-2 block target="_blank">
  全屏观看
</a>

<ClientOnly>
<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">
  <iframe :src="url" frameborder="0" style="position: absolute; top:0; left:0; width:100%; height:100%;" allowfullscreen></iframe>
</div>
</ClientOnly>

<script setup>
import { withBase } from 'vitepress'
const url = withBase('/midterm/index.html')
</script>
