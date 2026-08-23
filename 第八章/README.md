# 第八章 · 记忆与检索

> 基于 Datawhale [hello-agents](https://github.com/datawhalechina/hello-agents) 教程第八章「记忆与检索」的实战代码,用云服务(Qdrant + Neo4j + 讯飞星火 Embedding)跑通记忆系统与 RAG 检索增强生成的完整链路。

## 目录结构

```
第八章/
├── README.md              # 本说明文档
├── .env                   # 环境变量(需自行配置,见下文;含真实密钥,勿提交 git)
├── compat_shim.py         # 兼容垫片:让 hello-agents v0.2.0 跑在新版 qdrant-client / Neo4j Aura 上
├── env_init.py            # 环境自检:逐一验证 LLM / Embedding / Qdrant / Neo4j 四项连通性
├── demo_memory.py         # 演示一:记忆系统(工作/情景/语义记忆的增删查、遗忘、整合)
├── demo_rag.py            # 演示二:RAG 检索增强生成(文档加载→分块→检索→智能问答)
├── demo_agent.py          # 演示三:记忆与检索增强智能体(基线 vs 记忆增强 vs 检索增强 vs 联合)
├── sample_knowledge.md    # RAG 演示用的样例知识源文档
├── knowledge_base/        # RAG 临时知识库目录(add_text 落临时 .md 用,自动创建)
└── memory_data/           # 记忆系统本地 SQLite 存储目录(自动创建)
```

## 快速开始

### 1. 环境要求

- Python 3.10+(本教程使用 Anaconda 环境 `langchain_env`,解释器 `E:/anaconda_install/envs/langchain_env/python.exe`)
- 已安装 `hello-agents` 框架(`pip install hello-agents`)
- 依赖包:`qdrant-client`、`neo4j`、`python-dotenv`、`markitdown`、`spacy`(+ 中英文模型 `zh_core_web_sm` / `en_core_web_sm`)、`sentence-transformers`

> ⚠️ `hello-agents v0.2.0` 与新版 `qdrant-client>=1.19` 存在四处不兼容(详见 `compat_shim.py` 注释)。本目录的 `compat_shim.py` 已统一打补丁,**所有 demo 都会在 `import hello_agents.*` 之前先 `import compat_shim`**,无需额外操作。

### 2. 配置 `.env`

在**项目根目录**(即 `第八章/` 的上一级)放置 `.env`,关键变量如下(值需替换为你自己的):

```dotenv
# ---- LLM(stepfun,框架默认 OpenAI 兼容接口) ----
LLM_API_KEY=your_stepfun_api_key
LLM_MODEL_ID=step-3.7-flash
LLM_BASE_URL=https://api.stepfun.com/step_plan/v1

# ---- Embedding(讯飞星火 MaaS · Qwen3-Embedding-8B,768 维) ----
EMBED_MODEL_TYPE=dashscope
EMBED_MODEL_NAME=xop3qwen8bembedding
EMBED_API_KEY=your_xfyun_api_key
EMBED_BASE_URL=https://maas-api.cn-huabei-1.xf-yun.com/v2

# ---- Qdrant 云向量数据库 ----
QDRANT_URL=https://xxxx-xxxx.aws.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=hello_agents_vectors
QDRANT_VECTOR_SIZE=768    # 必须与 embedding 实际维度一致

# ---- Neo4j Aura 图数据库 ----
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USERNAME=xxxx        # Aura 的用户名即 home database 名,不是 neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=neo4j       # 垫片会在运行时自动回退到用户名同名库,无需手改

# ---- SerpApi(本章 demo 未用到,保留即可) ----
SERPAPI_API_KEY=your_serpapi_key
```

### 3. 跑通顺序

建议按以下顺序运行,每一步都确认 `✅` 通过后再进入下一步:

```bash
# 第 0 步:环境自检(四项服务连通性 + 向量维度对齐)
python env_init.py

# 第 1 步:记忆系统演示
python demo_memory.py

# 第 2 步:RAG 检索增强生成演示
python demo_rag.py

# 第 3 步:记忆与检索增强智能体演示
python demo_agent.py
```

## 各模块详解

### `compat_shim.py` —— 兼容垫片(本教程能跑通的关键)

`hello-agents v0.2.0` 在新版依赖上有四处不兼容,本模块统一打补丁:

| 问题                                                         | 根因                                                                                                                            | 垫片修复                                                                         |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `ImportError: qdrant-client未安装`                         | 框架`from qdrant_client.http.models import SearchRequest`,而 `SearchRequest` 在 1.19 被移除,导致 `QDRANT_AVAILABLE=False` | 往`qdrant_client.http.models` **包对象**注入空 `SearchRequest` 别名    |
| `'QdrantClient' object has no attribute 'search'`          | 1.19 移除了`client.search`,改用 `query_points`                                                                              | 给`QdrantClient` 补 `search`/`search_batch` 方法,内部转调 `query_points` |
| `'CollectionInfo' object has no attribute 'vectors_count'` | 1.19 改名为`points_count`                                                                                                     | 给`CollectionInfo` 补 `vectors_count` property                               |
| `Neo.ClientError.Database.DatabaseNotFound: 'neo4j'`       | Aura 的 home database = 用户名,非`neo4j`;且报错在 `session.run()` 惰性抛出                                                  | 在框架读取`NEO4J_DATABASE` 前,把环境变量回退为用户名                           |

> 🔑 **关键陷阱**:`from qdrant_client.http import models` 返回的是**子模块** `models.models`(因 `http/__init__.py` 第 11 行 re-export),而框架的 `from qdrant_client.http.models import X` 解析的是 **包对象** `sys.modules['qdrant_client.http.models']`。两者是不同对象,注入到其一不影响另一个。垫片用 `importlib.import_module("qdrant_client.http.models")` 精准拿到包对象再注入。

### `env_init.py` —— 环境自检

逐一验证四项服务的连通性并给出向量维度对齐提示:

- `check_llm`:发一句话请求验证 LLM
- `check_embedding`:探测 embedding 实际维度,确认与 `QDRANT_VECTOR_SIZE` 一致
- `check_qdrant`:连接云 Qdrant 并列出现有集合(旧维度集合需删除重建)
- `check_neo4j`:跑 `RETURN 1` 验证图数据库连通

### `demo_memory.py` —— 记忆系统

用 `MemoryTool` 演示记忆生命周期,核心是 `run({"action": ...})` 统一接口:

- **添加**(`add`):向 working/episodic/semantic 三类记忆各写入样本,展示 `importance` 分级
- **搜索**(`search`):语义向量召回,支持按 `memory_type` 过滤
- **遗忘**(`forget`):`importance_based` 策略,遗忘低价值记忆
- **整合**(`consolidate`):把重要的工作记忆提升为情景记忆(短期→长期)
- **统计**(`stats`/`summary`):记忆数量、类型分布、重要记忆 Top-N

> 四类记忆:工作记忆(working,短期临时)、情景记忆(episodic,具体事件)、语义记忆(semantic,通用知识)、程序记忆(procedural,技能流程)。

### `demo_rag.py` —— RAG 检索增强生成

用 `RAGTool` 走通 RAG 完整链路,核心是 `run({"action": ...})`:

- **添加文档**(`add_text` / `add_document`):文本直写或索引 Markdown 文件,内部走 MarkItDown 解析 + 段落级分块 + 向量化入库
- **检索对比**(`search`):同一问题对比普通检索 vs 高级检索(MQE 多查询扩展 + HyDE 假设文档嵌入)
- **智能问答**(`ask`):检索 Top-K → 拼 context → LLM 生成 → 附引用来源与相似度
- **统计**(`stats`):知识库向量数、维度、距离度量

> RAG 标准流程:文档加载 → 分块 → 向量化 → 存储 → 检索 → 生成。

### `demo_agent.py` —— 记忆与检索增强智能体

用 `SimpleAgent` 展示记忆与检索如何增强一个对话智能体,通过手动把检索结果注入 prompt 来对比增强效果:

- **基线对话**:无任何增强的 SimpleAgent,作对照
- **记忆增强**:写入用户偏好 → 检索记忆 → 注入 prompt → 个性化作答
- **检索增强**:RAG 检索知识 → 注入 prompt → 基于事实作答
- **联合增强**:记忆(你是谁)+ 检索(知识库)同时注入,最完整的增强

> 这里用手动注入 prompt 的方式展示增强机制本身。`SimpleAgent` 还支持 `ToolRegistry` 自主工具调用(`[TOOL_CALL:name:params]` 格式),框架会自动解析执行,详见框架源码 `simple_agent.py`。

## 常见问题

**Q: 报 `ImportError: qdrant-client未安装`,但我明明装了?**
A: 这是 `compat_shim` 要解决的问题。确认 demo 文件开头是 `import compat_shim` 在 `from hello_agents...` 之前,且 `compat_shim.py` 与 demo 在同一目录。

**Q: 报 `database 'neo4j' does not exist`?**
A: Neo4j Aura 的 home database 是用户名同名库,不是 `neo4j`。`.env` 里 `NEO4J_DATABASE=neo4j` 不用改,垫片会在运行时自动回退。若仍报错,确认 `NEO4J_USERNAME` 是 Aura 控制台显示的用户名。

**Q: 向量维度不对,集合创建失败?**
A: 运行 `python env_init.py` 看 `check_embedding` 输出的实际维度,确保 `.env` 的 `QDRANT_VECTOR_SIZE` 与之一致(讯飞 Qwen3-Embedding-8B 是 768)。若 Qdrant 上已有旧维度集合,需在 Qdrant 控制台删除后让框架重建。

**Q: `demo_rag.py` 的高级检索很慢?**
A: 高级检索(MQE+HyDE)会多次调用 LLM 生成子问题与假想答案,耗时正常。演示中已对部分步骤用普通检索(`enable_advanced_search=False`)提速。

## 学习要点

1. **记忆四分类**:working / episodic / semantic / procedural,对应人脑不同记忆机制。
2. **记忆生命周期**:编码 → 存储 → 检索 → 整合 → 遗忘,整合与遗忘是让记忆系统可持续的关键。
3. **RAG 六步**:加载 → 分块 → 向量化 → 存储 → 检索 → 生成,检索质量决定生成质量。
4. **高级检索**:MQE 提升召回率(多角度问),HyDE 拉近问题与答案的向量分布(假想答案)。
5. **向量 + 图双库**:Qdrant 存向量做相似度召回,Neo4j 存关系做多跳推理,互补。
6. **增强的本质**:把外部信息(记忆/知识)注入 prompt,让模型基于上下文而非纯参数化知识作答。
