---
theme: seriph
background: https://cdn.jsdelivr.net/gh/USTCdev/slidev-theme-ustc@master/assets/backgrounds/bg2.jpg
title: IOSYS
mdc: true
colorSchema: light
canvasWidth: 800
routerMode: hash
---

# Team IOSYS

<div class="text-4 op-80">

熊桐睿 张海川 朱雨田 许逸凡 冉竣宇 徐铭凯

</div>

---
zoom: 0.85
---

Why{.sect}

## 往年项目

- [My-Glow (2023)](https://github.com/OSH-2023/My-Glow) 基于 [Wowkiddy (2022)](https://github.com/OSH-2022/x-WowKiddy) 和 [TOBEDONE (2022)](https://github.com/OSH-2022/x-TOBEDONE) 

  ✅ 分布式框架优化、鲁棒性监控 <br>
  ⚠️ 传统打标方法 [✨ LlamaIndex]{.float-right.mr-50}

- [ArkFS (2024)](https://github.com/OSH-2024/ArkFS)

  ✅ 多模态向量化、二分图映射 <br>
  ⚠️ 图结构简化 [✨ 知识图谱]{.float-right.mr-50}

- [vivo50 (2024)](https://github.com/OSH-2024/vivo50)

  ✅ 自然语言/语音交互、任务序列转换 <br>
  ⚠️ RAG架构限制 [✨ Tool call]{.float-right.mr-50}

<div v-drag="[389,168,310,282]" border="3 yellow-500 dashed rounded-xl" pt-1 pl-2 text-yellow-600>
我们的改进
</div>

---
zoom: 0.85
---

Why{.sect}

## The [AIOS]{.text-4xl} [Trend]{.text-primary}

<div flex justify-center>
<img src="/../assets/research/image-1.png" w-160 mt-2 ml--4 />
</div>

---
layout: fact
class: bg-black bg-op-10
---

## 真正的意义是什么？

为什么这些 LLM+FS 系统，都没有流行起来？

<div flex justify-center items-center mt-6>
我们真的那么需要
<div inline-flex flex-col text-sm>
<div> “删除电脑中一张包含一棵树的图片” </div>
<div> “寻找我的身份证正反面照片” </div>
</div>
吗？
</div>


---

What{.sect}

### 我们要做什么

更强大的文件系统 Agent {.text-3xl.underlined.mb-4}

- 用自然语言进行文件操作
- 用图形式重新组织文件
- 提升增删查改等操作的效率

---
zoom: 0.85
---

What{.sect}

## 创新点

<div v-drag="[85,141,400,95]">

### 1. 深度语义理解驱动的文件管理

- 超越关键字和元数据
- 自然语言成为一级交互界面

</div>

<div v-drag="[542,201,335,127]">

### 2. 图状文件组织范式

- 编码大量的异构和关系信息
- 多维度的语义标签
- 多对多的关系映射

</div>

<div v-drag="[150,347,583,159]">

### 3. 全面的语义信息集成

- 集成各个方面的语义信息[（元数据、文件间关系、用户交互历史等）]{.text-sm.op-80}
- 更细粒度的数据

</div>

---

What{.sect}

### The Additional Capability

<div text-3xl mt-2 underlined mb-1> Agent2Agent Protocol (A2A) </div>
<div italic text-4 op-80>(Proposed by Google, 2025.4.9)</div>

<img v-drag="[55,187,336,NaN]" src="https://a2aproject.github.io/A2A/latest/assets/a2a-mcp-readme.png" />

<div fixed inset-2 border="yellow 4 rounded-4" />

<div v-drag="[454,238,308,NaN]" border="1.5 black op-70 rounded-xl" px-2 py-1>

### A2A or MCP? {.mb-2.text-primary}

- A2A: How agents collaborate
- MCP: How functions are provided
- No conflict

</div>

---

What{.sect}

## 总体架构

![arch](/../assets/arch.svg){.w-100.ml--3}

---

How{.sect}

### 如何让大模型调用外部工具？{.op-80}

Tool & Function Calling {.text-3xl.underlined.mb-4}

```py {*}{class:'w-100'}
tools = [{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get current temperature.",
    "parameters": {
      ...
    }
  }
}]
```

<img src="/../assets/feasibility/function-call.png" fixed top-0 right-0 h-full rounded-8 />

---

How{.sect}

### 如何保证输出符合格式？{.op-80}

Structured Outputs {.text-3xl.underlined.mb-4}

强制要求 LLM 的输出严格遵守用户提供的 JSON Schema {.text-2xl}

- 可靠的指令生成
- 精确的数据提取
- 简化下游处理
- 类型安全

---

How{.sect}

### 复杂文件的文本化？{.op-80}

[Microsoft/markitdown](https://github.com/microsoft/markitdown){.text-2xl}

```mermaid {scale:0.6}
graph LR;
A[PDF] -----> E((markitdown))
B[Word] -----> E
C[PPT] -----> E
D[Excel] -----> E
E ----> F[Markdown] ----> G((LLM))
```

<div v-drag="[439,75,315,NaN]" border="1.5 black op-70 rounded-xl" px-2 py-1>

### Embedded image? {.mb-2.text-primary}

- Fork [Microsoft/markitdown]{.font-mono.ml-1}
- Convert to text description
- As separate images with links

</div>

---

<img src="https://microsoft.github.io/graphrag/img/GraphRag-Figure1.jpg" z--1 fixed op-40 inset-y-20 right-0 />

How{.sect}

### 信息提取和检索？{.op-80}

GraphRAG {.text-3xl.underlined.mb-4}

1. **图结构知识库**：知识库通过图来表示，其中节点代表实体，边表示实体之间的关系
2. **图检索 [(Graph Retrieval)]{.text-sm}**：通过节点和边来寻找相关信息，具备更强的关系推理能力
3. **增强生成 [(Generation)]{.text-sm}**：结合检索到的图信息，生成更加精准和上下文相关的回答

---

How{.sect}

### 分布式？{.op-80}

JuiceFS {.text-3xl.underlined.mb-4}

![logo](https://github.com/juicedata/juicefs/raw/main/docs/en/images/juicefs-logo-new.svg){.fixed.right-2.top-10.scale-70}

<div text-xl mt-8>

- 云原生文件存储，分布式，支持多种存储后端
- 相比 Ceph 和 3FS 的优势：跨平台，泛用性强，容易二次开发

</div>

<div italic op-80 mt-8>
Not new but it works!
</div>

---
class: mt--4
---

Recap{.sect}

## 我们的架构图 <span text-lg italic op-80> Work in Progress... </span>

![arch](/../assets/arch.svg){.w-120.ml--4.mt--4}

<div v-drag="[530,139,40,NaN]" h-20 i-vscode-icons-file-type-typescript-official />

<div v-drag="[530,230,40,NaN]" h-20 i-vscode-icons-file-type-python />

<div v-drag="[530,324,40,NaN]" h-20 i-vscode-icons-file-type-python />

---
layout: end
---

Thanks!
