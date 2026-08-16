"""
ReAct 智能体项目入口。

功能: 组装 LLM 客户端(llm.py)、工具执行器(tools.py)与 ReAct 智能体(reactagent.py),提供交互式问答入口。
创建日期: 2026-08-15

输入:
  .env 环境变量(LLM_* 与 SERPAPI_API_KEY)
  终端标准输入:用户问题(输入 exit 或 q 退出;启动时无命令行参数则先跑一个演示问题)

输出: 控制台打印每轮 Thought/Action/Observation 与最终答案,无文件产物

用法:
  python main.py            # 先跑内置演示问题,再进入交互问答
"""

import sys

# Windows 控制台默认 GBK 编码,打印 emoji 会抛 UnicodeEncodeError,这里强制 UTF-8 输出
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from llm import HelloAgentsLLM
from tools import ToolExecutor, search
from reactagent import ReActAgent


def build_agent(max_steps: int = 5, debug: bool = False) -> ReActAgent:
    '''
    组装 ReAct 智能体:创建 LLM 客户端 → 注册工具 → 实例化智能体。

    入参: max_steps 最大推理轮数; debug 是否打印 LLM 原始 chunk 数据包
    返回: 可直接调用 run(question) 的 ReActAgent 实例
    '''
    # 1. 创建 LLM 客户端(配置来自 .env)
    llm_client = HelloAgentsLLM(debug=debug)

    # 2. 初始化工具执行器并注册搜索工具
    tool_executor = ToolExecutor()
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时,应使用此工具。"
    tool_executor.registerTool("Search", search_description, search)

    # 3. 实例化 ReAct 智能体
    return ReActAgent(llm_client=llm_client, tool_executor=tool_executor, max_steps=max_steps)


if __name__ == '__main__':
    # debug 模式:python main.py debug 时打印 LLM 原始 chunk 数据包
    debug = len(sys.argv) > 1 and sys.argv[1] == "debug"
    agent = build_agent(debug=debug)

    # 内置演示问题:验证完整 ReAct 循环(需要实时信息,必然触发搜索工具)
    demo_question = "英伟达最新的GPU型号是什么"
    print(f"\n===== 演示问题: {demo_question} =====")
    answer = agent.run(demo_question)
    if not answer:
        print("演示问题未能获得答案。")

    # 交互式问答
    print("\n===== 进入交互问答(输入 exit 或 q 退出) =====")
    while True:
        try:
            question = input("\n你的问题: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question or question.lower() in ("exit", "q"):
            break
        agent.run(question)

    print("再见!")
