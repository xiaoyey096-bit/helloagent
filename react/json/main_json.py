"""
JSON 版 ReAct 入口: 组装使用 JSON 结构化协议的 ReAct 智能体,与文本版(react/main.py)跑同一组问题便于对比。

build_agent: 创建 LLM 客户端 → 注册 Search 工具 → 实例化 ReActJsonAgent
用法: python react/json/main_json.py(先跑内置演示问题再进入交互问答,输入 exit/q 退出)
"""

import os
import sys

# 本脚本在 react/json/ 子目录,把上级 react/ 目录加入模块搜索路径,才能共用其 llm.py 与 tools.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 控制台默认 GBK 编码,打印 emoji 会抛 UnicodeEncodeError,这里强制 UTF-8 输出
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from llm import HelloAgentsLLM
from tools import ToolExecutor, search
from reactagent_json import ReActJsonAgent


def build_agent(max_steps: int = 5, debug: bool = False) -> ReActJsonAgent:
    '''组装 JSON 版 ReAct 智能体:创建 LLM 客户端 → 注册工具 → 实例化智能体。'''
    llm_client = HelloAgentsLLM(debug=debug)

    tool_executor = ToolExecutor()
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时,应使用此工具。"
    tool_executor.registerTool("Search", search_description, search)

    return ReActJsonAgent(llm_client=llm_client, tool_executor=tool_executor, max_steps=max_steps)


if __name__ == '__main__':
    # debug 模式:python main_json.py debug 时打印 LLM 原始 chunk 数据包
    debug = len(sys.argv) > 1 and sys.argv[1] == "debug"
    agent = build_agent(debug=debug)

    # 与文本版 main.py 相同的演示问题,便于横向对比两种解析方案
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
