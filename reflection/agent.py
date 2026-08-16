"""
Reflection 智能体: 执行→反思→优化的迭代自我纠错范式,依靠短期记忆串联多轮轨迹。

ReflectionAgent: 反思智能体;run() 先生成初稿,再循环"评审员反思→判定无需改进即收敛→按反馈修订",最多 max_iterations 轮
"""

from llm import HelloAgentsLLM
from memory import Memory
from prompts import INITIAL_PROMPT_TEMPLATE, REFLECT_PROMPT_TEMPLATE, REFINE_PROMPT_TEMPLATE


class ReflectionAgent:
    '''反思智能体:同一个 llm_client 依次扮演"程序员"与"评审员"两个角色,memory 存轨迹,max_iterations 限制轮数。'''

    def __init__(self, llm_client: HelloAgentsLLM, max_iterations: int = 3):
        self.llm_client = llm_client
        self.memory = Memory()
        self.max_iterations = max_iterations

    def run(self, task: str) -> str:
        '''运行完整循环:初稿→(反思→收敛判定→修订)×N,返回最终代码。'''
        print(f"\n--- 开始处理任务 ---\n任务: {task}")

        # --- 1. 初始执行:生成"初稿" ---
        print("\n--- 正在进行初始尝试 ---")
        initial_prompt = INITIAL_PROMPT_TEMPLATE.format(task=task)
        initial_code = self._get_llm_response(initial_prompt)
        self.memory.add_record("execution", self._extract_code(initial_code))

        # --- 2. 迭代循环:反思与优化 ---
        for i in range(self.max_iterations):
            print(f"\n--- 第 {i+1}/{self.max_iterations} 轮迭代 ---")

            # a. 反思:评审员审视最新代码
            print("\n-> 正在进行反思...")
            last_code = self.memory.get_last_execution()
            reflect_prompt = REFLECT_PROMPT_TEMPLATE.format(task=task, code=last_code)
            feedback = self._get_llm_response(reflect_prompt)
            self.memory.add_record("reflection", feedback)

            # b. 收敛判定:评审员认为无需改进则提前结束(容忍几种同义表述)
            if any(keyword in feedback for keyword in ("无需改进", "无需进一步", "不需要改进")):
                print("\n✅ 反思认为代码已无需改进，任务完成。")
                break

            # c. 优化:按评审反馈修订代码
            print("\n-> 正在进行优化...")
            refine_prompt = REFINE_PROMPT_TEMPLATE.format(
                task=task,
                last_code_attempt=last_code,
                feedback=feedback
            )
            refined_code = self._get_llm_response(refine_prompt)
            self.memory.add_record("execution", self._extract_code(refined_code))

        final_code = self.memory.get_last_execution()
        print(f"\n--- 任务完成 ---\n最终生成的代码:\n```python\n{final_code}\n```")
        return final_code

    def _get_llm_response(self, prompt: str) -> str:
        '''调用 LLM 并返回完整流式响应,失败返回空串。'''
        messages = [{"role": "user", "content": prompt}]
        return self.llm_client.think(messages=messages) or ""

    def _extract_code(self, response: str) -> str:
        '''从模型回复中剥掉 markdown 代码围栏只留纯代码,避免围栏在记忆里层层嵌套污染后续提示词。'''
        text = response.strip()
        if "```" in text:
            parts = text.split("```")
            # 取最长的一段,通常就是代码主体;去掉可能开头的 python 语言标记
            code = max(parts, key=len).strip()
            if code.startswith("python"):
                code = code[6:].strip()
            return code
        return text
