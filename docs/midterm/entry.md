---
aside: false
---

# 中期报告

<ClientOnly>
<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;" class="mt-6">
  <iframe :src="url" frameborder="0" style="position: absolute; top:0; left:0; width:100%; height:100%;" allowfullscreen></iframe>
</div>
</ClientOnly>

<div mt-2 text-xl>
(
<span op-80>悬停于幻灯片左下角以导航</span>
or
<a :href="url" target="_blank">全屏观看</a>
)
</div>

<script setup>
import { withBase } from 'vitepress'
const url = withBase('/midterm/index.html')
</script>
