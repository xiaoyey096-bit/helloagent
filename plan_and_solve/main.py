"""
Plan-and-Solve 项目入口: 组装 LLM 客户端与两阶段智能体,提供演示问题与交互问答。

build_agent: 创建 LLM 客户端并实例化 PlanAndSolveAgent(内部自带规划器与执行器)
用法: python main.py(先跑内置演示问题再进入交互问答,输入 exit/q 退出;python main.py debug 打印原始 chunk)
"""

import sys

# Windows 控制台默认 GBK 编码,打印 ✅/❌ 等 emoji 会抛 UnicodeEncodeError,这里强制 UTF-8 输出
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from llm import HelloAgentsLLM
from agent import PlanAndSolveAgent


def build_agent(debug: bool = False) -> PlanAndSolveAgent:
    '''组装 Plan-and-Solve 智能体:创建 LLM 客户端 → 实例化智能体。'''
    llm_client = HelloAgentsLLM(debug=debug)
    return PlanAndSolveAgent(llm_client=llm_client)


if __name__ == '__main__':
    # debug 模式:python main.py debug 时打印 LLM 原始 chunk 数据包
    debug = len(sys.argv) > 1 and sys.argv[1] == "debug"
    agent = build_agent(debug=debug)

    # 内置演示问题:包含三个可分解的子问题,天然适合"先规划后执行"
    demo_question = "苏轼是哪个朝代的人?他的代表作有哪些?请用一句话总结他的文学成就。"
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
