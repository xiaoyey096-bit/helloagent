"""
Plan-and-Solve 智能体: 先规划(Planner 生成步骤列表)后执行(Executor 逐步求解)的两阶段范式。

Planner: 规划器,plan() 让 LLM 分解问题并用 ast.literal_eval 从 ```python 代码块解析出步骤列表
Executor: 执行器,execute() 按计划逐步调用 LLM,历史结果逐步累积回填,最后一步的输出即最终答案
PlanAndSolveAgent: 智能体,run() 串联"规划→执行";计划解析失败则提前终止
"""

import ast

from llm import HelloAgentsLLM
from prompts import PLANNER_PROMPT_TEMPLATE, EXECUTOR_PROMPT_TEMPLATE


class Planner:
    '''规划器:把复杂问题分解为有序的步骤列表。'''

    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def plan(self, question: str) -> list[str]:
        '''生成并解析行动计划,解析失败返回空列表。'''
        prompt = PLANNER_PROMPT_TEMPLATE.format(question=question)
        messages = [{"role": "user", "content": prompt}]

        print("--- 正在生成计划 ---")
        response_text = self.llm_client.think(messages=messages) or ""
        print(f"\n✅ 计划已生成:\n{response_text}")

        try:
            # 找到```python和```之间的内容,再用 ast.literal_eval 安全地把字符串转成 Python 列表
            plan_str = response_text.split("```python")[1].split("```")[0].strip()
            plan = ast.literal_eval(plan_str)
            return plan if isinstance(plan, list) else []
        except (ValueError, SyntaxError, IndexError) as e:
            print(f"❌ 解析计划时出错: {e}")
            print(f"原始响应: {response_text}")
            return []
        except Exception as e:
            print(f"❌ 解析计划时发生未知错误: {e}")
            return []


class Executor:
    '''执行器:按计划逐步调用 LLM 求解,历史结果逐步累积。'''

    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def execute(self, question: str, plan: list[str]) -> str:
        '''按序执行每个步骤并返回最后一步的结果。'''
        history = ""  # 已完成步骤与结果的累积记录
        response_text = ""  # 空计划时避免最后取值报错(正常流程由 run() 挡住空计划)

        # 完整计划格式化成编号列表,比直接 str(plan) 更利于模型阅读
        plan_text = "\n".join(f"{j + 1}. {s}" for j, s in enumerate(plan))

        print("\n--- 正在执行计划 ---")
        for i, step in enumerate(plan):
            print(f"\n-> 正在执行步骤 {i + 1}/{len(plan)}: {step}")

            prompt = EXECUTOR_PROMPT_TEMPLATE.format(
                question=question,
                plan=plan_text,
                history=history if history else "无",  # 第一步还没有历史
                current_step=step,
            )
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages) or ""

            # 本步结果写入历史,供后面的步骤参考
            history += f"步骤 {i + 1}: {step}\n结果: {response_text}\n\n"
            print(f"✅ 步骤 {i + 1} 已完成")

        # 循环结束后,最后一步的响应就是最终答案
        return response_text


class PlanAndSolveAgent:
    '''两阶段智能体:先规划后执行。'''

    def __init__(self, llm_client: HelloAgentsLLM):
        '''初始化智能体,同时创建规划器和执行器。'''
        self.llm_client = llm_client
        self.planner = Planner(llm_client)
        self.executor = Executor(llm_client)

    def run(self, question: str) -> str:
        '''完整流程:规划失败提前终止,成功则执行计划并返回最终答案。'''
        print(f"\n--- 开始处理问题 ---\n问题: {question}")

        # 1. 调用规划器生成计划
        plan = self.planner.plan(question)
        if not plan:
            print("\n--- 任务终止 --- \n无法生成有效的行动计划。")
            return None

        # 2. 调用执行器执行计划
        final_answer = self.executor.execute(question, plan)

        print(f"\n--- 任务完成 ---\n最终答案: {final_answer}")
        return final_answer
