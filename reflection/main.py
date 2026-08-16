"""
Reflection 项目入口: 组装 LLM 客户端与反思智能体,提供演示任务与交互问答。

build_agent: 创建 LLM 客户端并实例化 ReflectionAgent(内部自带短期记忆)
用法: python main.py(先跑内置演示任务再进入交互,输入 exit/q 退出;python main.py debug 打印原始 chunk)
"""

import sys

# Windows 控制台默认 GBK 编码,打印 📝/✅ 等 emoji 会抛 UnicodeEncodeError,这里强制 UTF-8 输出
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from llm import HelloAgentsLLM
from agent import ReflectionAgent


def build_agent(max_iterations: int = 2, debug: bool = False) -> ReflectionAgent:
    '''组装反思智能体:创建 LLM 客户端 → 实例化智能体。'''
    llm_client = HelloAgentsLLM(debug=debug)
    return ReflectionAgent(llm_client=llm_client, max_iterations=max_iterations)


if __name__ == '__main__':
    # debug 模式:python main.py debug 时打印 LLM 原始 chunk 数据包
    debug = len(sys.argv) > 1 and sys.argv[1] == "debug"
    agent = build_agent(debug=debug)

    # 内置演示任务:课程 4.4 的素数任务,存在"试除法→埃氏筛法"的清晰优化路径,适合演示反思迭代
    demo_task = "编写一个Python函数，找出1到n之间所有的素数 (prime numbers)。"
    print(f"\n===== 演示任务: {demo_task} =====")
    code = agent.run(demo_task)
    if not code:
        print("演示任务未能生成代码。")

    # 交互式任务
    print("\n===== 进入交互任务(输入 exit 或 q 退出) =====")
    while True:
        try:
            task = input("\n你的任务: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not task or task.lower() in ("exit", "q"):
            break
        agent.run(task)

    print("再见!")
