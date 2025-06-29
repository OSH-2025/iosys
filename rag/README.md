以下内容是关于知识图谱模块的幻灯片草稿。

---

知识图谱这个术语最初由谷歌在 2012 年 5 月提出，作为其增强搜索结果，向用户提供更多上下文信息的一部分实践。知识图谱旨在理解实体之间的关系，并直接提供查询的答案，而不仅仅返回相关网页的列表。

知识图谱是一种以图结构形式组织和连接信息的方式，其中节点表示实体，边表示实体之间的关系。图结构允许用户高效地存储、检索和分析数据。

---

今天，我们可以利用大语言模型，提取文本中的实体与关系，以快速建立文本到知识图谱的对应。

对这一任务进行抽象后，大语言模型需要做的工作是：从输入文本中尽可能提取“主-谓-宾三元组”的结构，作为知识图谱的有向边，并将这些三元组输出为易被程序读取的格式（如 JSON）。

---

完成这一任务的 System Prompt 如下。我们将上文提到的工作向大语言模型作了清晰的描述。

>  You are an AI expert specialized in knowledge graph extraction. 
> Your task is to identify and extract factual Subject-Predicate-Object (SPO) triples from the given text.
> Focus on accuracy and adhere strictly to the JSON output format requested in the user prompt.
> Extract core entities and the most direct relationship.

---

User Prompt 模板的一部分如下。我们要求了大语言模型严格按格式输出，并要求简要的谓词、尽可能完整的结构，还要求了“将人称代词转化为具体的人名”这一大语言模型才能完成的特定任务。

>Please extract Subject-Predicate-Object (S-P-O) triples from the text below. 
>
>**VERY IMPORTANT RULES:**
>
>1. **Output Format:** Respond ONLY with a single, valid JSON array. Each element MUST be an object with keys "subject", "predicate", "object".
>
>2. **JSON Only:** Do NOT include any text before or after the JSON array (e.g., no 'Here is the JSON:' or explanations). Do NOT use markdown ```json ... ``` tags.
>
>   （其它规则下略）
>
>**Text to Process:** {text chunk}

---

在 IOSYS 中，知识图谱模块首先会将每个文件的知识图谱结构提取出来。对于非文本文件，我们会先用 markitdown 模块提取文本信息，再转换为知识图谱。

对于体积较小的单个文件，知识图谱模块会直接将该文件的信息送给 LLM 做关系提取；

对于文本信息较长的文件，为了保证 LLM 提取关系的有效性，我们先对文本用 jieba 作词语分割，将文本按词数分割成 chunks 送入，两个 chunk 中存在可以指定的重叠（overlap），在分别提取关系后再将所有三元组合并。

---

由于 LLM 生成的 JSON 可能出现重复、错误等情况，我们可以在后续的解析阶段将数据进行进一步处理，以使得知识图谱更为紧凑。

这里对 LLM 输出结果的处理有：标准化（英文单词全部转化为小写），过滤空文本（三元组中任一词为空则过滤），去重复。

每次更新文件知识图谱，知识图谱模块就会完成一系列 LLM 请求，将文件文本信息转化为三元组 JSON 并进一步处理，得到理想的知识图谱。

---

（可以展示单个文件的提取效果）

---

关联性较高的文件中会存在相同的实体或关系。IOSYS 的处理是将多个文件的知识图谱进行合并，以得到一张整个文件系统的知识图谱。

（可以先展示几个文件的知识图谱）

---

（再展示合并后的结果）

---

这样，我们就可以在文件系统的知识图谱上，对文件系统进行增删改查等操作。

（演示操作前后知识图谱可能的变化）

---

知识图谱模块的 LLM 交互是时间瓶颈，生成文件系统的知识图谱结构可能需要花费较长时间。

因此我们将知识图谱模块设计为了完全异步的结构，并对每个（可生成知识图谱的）文件节点都实例化一个知识图谱模块类，在得到请求后并行向 LLM 发出多个请求，用异步 IO 的思想优化了处理的效率。

---

生成的知识图谱会保存在文件的元数据中，以避免重复生成。

每次请求得到文件的知识图谱，知识图谱模块都会先在元数据中寻找知识图谱信息；若知识图谱存在且无误，模块就会直接加载现有的知识图谱数据，否则再申请生成。

同时，在元数据中保存文件的语义结构信息，便于其它系统模块的访问。

---

