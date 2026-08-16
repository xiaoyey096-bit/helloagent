# Hello Agent 学习项目

Datawhale hello-agent 课程实战:用最少的依赖从零实现两种智能体范式,共用同一个 LLM 客户端(从项目根的 `.env` 读取配置)。

## 目录结构

```
hello agent/
├── react/                     # ReAct 范式:边想边做,可调用外部搜索工具
│   ├── main.py                # 入口:python react/main.py(加 debug 参数打印原始 chunk)
│   ├── reactagent.py          # Thought→Action→Observation 循环(正则解析版)
│   ├── llm.py                 # LLM 流式客户端
│   ├── prompts.py             # 提示词模板
│   ├── tools.py               # SerpApi 搜索工具与工具执行器
│   ├── json/                  # JSON 协议版(4.2 思考题):入口 python react/json/main_json.py
│   │   ├── reactagent_json.py # json_object 模式 + 防御性解析的智能体
│   │   ├── prompts_json.py    # JSON 协议提示词模板
│   │   └── main_json.py       # JSON 版入口(共用上级 llm.py / tools.py)
│   └── reactagent执行链路.html # 执行链路架构图
├── plan_and_solve/            # Plan-and-Solve 范式:先规划后执行,纯 LLM 问答
│   ├── main.py                # 入口:python plan_and_solve/main.py
│   ├── agent.py               # Planner + Executor + PlanAndSolveAgent
│   ├── llm.py                 # LLM 流式客户端(与 react/ 同一实现)
│   ├── prompts.py             # 规划/执行两个模板
│   └── planandsolve执行链路.html # 执行链路架构图
├── OpenAI数据包形式.py         # 流式 chunk 数据包的教学观察示例
├── 基础知识/                   # 学习笔记
└── .env                       # 密钥配置(已被 .gitignore 忽略,切勿提交)
```

两个文件夹各自独立、互不依赖,在项目根目录直接运行即可(`.env` 放在根目录,两个入口都会自动向上找到它)。

## 两种范式对比

| | ReAct | Plan-and-Solve |
|---|---|---|
| 决策方式 | 每轮根据观察动态决定下一步 | 开始时一次性生成完整计划 |
| 外部工具 | SerpApi 谷歌搜索 | 无,全程纯 LLM 问答 |
| 循环中传递 | Thought/Action/Observation 历史 | 已完成步骤 + 结果的历史 |
| 正常出口 | `Action: Finish[答案]` | 计划的最后一步输出 |
| 兜底出口 | 超过 max_steps 强制总结 | 计划解析失败直接终止 |
