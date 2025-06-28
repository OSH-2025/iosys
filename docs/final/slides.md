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

为什么这些 LLM+FS 系统，都（还）没有流行起来？

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

What{.sect.mt--2!}

### The Additional Capability

<div text-3xl mt-2 underlined mb-1> Agent2Agent Protocol (A2A) </div>
<div italic text-4 op-80>(Proposed by Google, 2025.4.9)</div>

<img v-drag="[55,163,369,NaN]" src="https://a2aproject.github.io/A2A/latest/assets/a2a-mcp-readme.png" />

<div fixed inset-2 border="yellow 4 rounded-4" />

<div v-drag="[458,179,308,NaN]" border="1.5 black op-70 rounded-xl" px-2 py-1>

### A2A or MCP? {.mb-2.text-primary}

- A2A: How agents collaborate
- MCP: How functions are provided
- No conflict

</div>

---

<img fixed h-full top-0 src="./assets/arch.svg" />

---

<img fixed h-full top-0 src="./assets/arch.svg" />

<FocusOn :left="340" :top="185" :radius="120" />

---

# Server & Agent

## Agent: 用户交互的枢纽

<br>

1. 处理用户请求
2. 使用 LLM 进行自然语言理解
3. 调用工具获取信息/执行操作

<img v-drag="[432,102,282,NaN]" src="./assets/agent.svg" rounded-lg />

---

# Server & Agent

## Tool Call

LLM 调用外部工具的方式

<br>

- **获取信息**：读取文件内容 / 绘制图表
- **执行操作**：创建目录 / 生成文档

---

# Server & Agent

## Tool Call

<br>

- **多轮调用**："请总结文件 a 的内容，并将结果保存到文件 b 中"

<br>

```mermaid
graph LR;
A((User Input)) --> B{LLM} -->|Tool Calls| C[Tools] -->|Actions| E[Real World];
C -->|Results| B;
B --> D((Response));
```


---

# Server & Agent

## Model Context Protocol (MCP)

<br>

- 最广泛采用的 Tool Call 协议
- 自由启用 / 关闭工具
- 支持官方 JSON 格式配置文件

<img v-drag="[331,155,444,NaN]" src="./assets/mcp.png" border="#AAA 1.5px rounded" />

---

# Server & Agent

## 


---

<img fixed h-full top-0 src="./assets/arch.svg" />

<FocusOn :left="310" :top="355" :radius="120" />

---

# FileSystem

<br>

- 一套接口，支持两种实现
  - **OSFS**：本地文件系统
  - **JFS**：JuiceFS 分布式文件系统

- 原生支持嵌入文件

- 原生支持元数据

```plantuml {scale:0.5,class:'fixed top--30 right--40'}
@startuml
'——布局与样式——
skinparam shadowing false
skinparam componentStyle rectangle
skinparam ranksep 30
skinparam dpi 150
'默认从上到下布局（不加 left to right direction）

'——顶层接口——
rectangle "IOSYS FileSystem API\n(Unified Interface)" as API #EFEFEF

'——抽象层（__init__.py）——
rectangle "__init__.py\nIOSYSFileSystem\nFileSystemNode" as ABSTRACT

'——实现层——
rectangle "osfs_impl.py\nOSFileSystem\nOSFileSystemNode" as OSFS
rectangle "jfs_impl.py\nJuiceFSFileSystem\nJuiceFSFileSystemNode" as JFS
rectangle "cache_impl.py\nCacheFileSystem\nCacheFileSystemNode" as CACHE

'——存储层（Local Disk）——
database "Local Disk" as DISK
folder "Disk Metadata\n(.meta file)" as DISK_META
folder "File Objects\n(file or .content)" as DISK_OBJ

'——存储层（JuiceFS Cloud）——
cloud "JuiceFS Cloud Service" as CLOUD
folder "Alibaba Cloud OSS\n(Object Storage)" as OSS
database "JuiceFS Meta DB\n(Redis / TiKV)" as META_DB

'——层级关系——
API --> ABSTRACT
ABSTRACT --> OSFS
ABSTRACT --> JFS
ABSTRACT --> CACHE

'——CacheFileSystem 组合关系——
CACHE ..> OSFS : wraps
CACHE ..> JFS  : wraps

'——OSFS → Local Disk——
OSFS --> DISK : uses
DISK --> DISK_META : stores
DISK --> DISK_OBJ  : stores

'——JFS → JuiceFS Cloud——
JFS --> CLOUD : uses
CLOUD --> OSS      : stores objects
CLOUD --> META_DB  : stores metadata
@enduml
```

---

# FileSystem

## “嵌入文件”

Word 中内嵌的图片，如何体现在文件系统中？<br>

- 统一文件与目录：<span block mt--2 />
  - 目录 $=$ 文件 $-$ 内容
  - 文件 $=$ 目录 $+$ 内容

- 嵌入文件作为原文件的子节点

- 嵌入文件具有一致操作接口

```mermaid {class:'fixed top-8 right-30'}
graph TB;
A(Root) --> B(Directory * n) --> C(File) --> D(Embedded File);
```

---

<img fixed h-full top-0 src="./assets/arch.svg" />

<FocusOn :left="560" :top="375" :radius="140" />

---

# File Parser

多模态数据的**解析**、**文本化**与**概要生成**
<div h-4 />

- 文本化功能基于修改后的 markitdown
- 使用 LLM 生成多层级概要
- 提取嵌入文件

<br>

- 便于索引和检索
- 节约后续操作的成本和时间

<img v-drag="[340,177,429,NaN]" src="./assets/parser.svg" rounded-lg />

---

# File Parser

<div v-drag="[18,104,350,NaN]">
<div text-sm ml-10> 输入: Word 文档 </div>
<img src="./assets/parser-example.png" />
</div>

<div v-drag="[354,-5,450,NaN]">


<div scale-80>

<div mb-2>
输出: 文本
</div>


```md {class:'children:children:text-sm!'}
![This diagram illustrates....](./optical analysis apparatus structure.png)

ZKY-GD-4 智能光电效应（普朗克常数）实验仪如上图所示。

实验数据记录以及分析处理基本必做实验内容

1. 零电流法、补偿法分别测遏止电压；
2. 饱和光电流与光强之间的变化关系。

1. 固定一种直径大小光阑的情况下，分别测量 5 种不同单色光照射下，光电流的遏止电压。

```

<div h-8 />

<div flex gap-8>
<div>
<div mb-1>
输出: 嵌入文件
</div>

```mermaid {scale:0.6}
graph LR;
A(讲义.docx) --> B(仪器结构图.png)
A --> C(操作面板.png)
A --> D(...)
```

</div><div>
<div>
输出: 元数据
</div>

<div text-4 mt-1>


- 文件类型： Word 文档
- 文件大小： 1.2 MB
- 创建时间： 1751116881663
- ...

</div>
</div>
</div>
</div>
</div>

---

<img fixed h-full top-0 src="./assets/arch.svg" />

<FocusOn :left="590" :top="124" :radius="50" />

---

# Knowledge Graph

借助大语言模型，提取文件中的实体与关系
<div h-4 />

- **输入：** 文本（来自于 File Parser 模块）
- **输出：** 尽可能多的 **“主-谓-宾”**（Subject-Predicate-Object）三元组。
- **格式：** 将三元组输出为易于程序读取的格式，如 JSON。

<div h-8 />

> **System Prompt**:
>
> You are an AI expert specialized in knowledge graph extraction. 
> Your task is to identify and extract factual Subject-Predicate-Object (SPO) triples from the given text.
> Focus on accuracy and adhere strictly to the JSON output format requested in the user prompt.
> Extract core entities and the most direct relationship.

---

# Knowledge Graph

### 工作流程

<div h-4 />

```mermaid {scale:0.54,class:'ml--2'}
graph LR
    subgraph "处理小文件"
        A(文件输入) -- 小 --> F[直接送入 LLM];
        F --> H_small(按 chunk 送入 LLM);
    end

    subgraph "处理大文件"
        A -- 大 --> G[Jieba: 文本分块];
        G --> H_large(按 chunk 送入 LLM);
    end
    
    subgraph "后续处理"
        H_small & H_large --> J[LLM: 提取三元组];
        J --> L[标准化/过滤/去重];
        L --> M(知识图谱);
    end
```

---

# Knowledge Graph

- **按需生成**：不是所有文件都需要知识图谱
- **持久化**：避免重复生成
- **合并展示**：支持合并展示目录中的所有知识图谱

---

<div text-xl mt--6>三体人物关系（部分）</div>

<img v-drag="[51,49,702,NaN]" src="./assets/kg-demo.png" rounded-md />

---

<img fixed h-full top-0 src="./assets/arch.svg" />

<FocusOn :left="530" :top="92" :radius="50" />

---

# File Graph



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
D[Excel] -----> E
X[...] -----> E
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
layout: end
---

Thanks!
