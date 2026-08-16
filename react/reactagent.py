"""
ReAct 智能体核心循环: Thought → Action → Observation 循环推理,直到 Finish 或达到最大步数。

ReActAgent: ReAct 智能体,run() 驱动主循环;含输出解析(_parse_output)、动作解析(_parse_action)与超步数强制总结(_force_final_answer)
"""

import re
from llm import HelloAgentsLLM
from tools import ToolExecutor
from prompts import REACT_PROMPT_TEMPLATE, FINAL_ANSWER_PROMPT_TEMPLATE


class ReActAgent:
    '''ReAct 智能体:llm_client 负责"思考",tool_executor 负责"行动",max_steps 防止无限循环。'''

    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []   # 每轮的 Thought/Action/Observation 文本记录

    def run(self, question: str) -> str:
        '''运行 ReAct 主循环回答问题:提示词→思考→解析→Finish返回/执行工具→观察入历史,超步数强制总结。'''
        self.history = []  # 每次运行时重置历史记录
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n========== 第 {current_step} 步 ==========")

            # 1. 格式化提示词(工具描述 + 问题 + 历史)
            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history) if self.history else "(空)"
            #三元条件表达式，变量 = 表达式A  if 条件 else 表达式B，，if成立则A，else B
            prompt = REACT_PROMPT_TEMPLATE.format(
                tools=tools_desc,
                question=question,
                history=history_str
            )

            # 2. 调用 LLM 进行思考
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)

            if not response_text:
                print("错误:LLM未能返回有效响应。")
                break

            # 3. 解析 LLM 的输出,提取 Thought 和 Action
            thought, action = self._parse_output(response_text)

            if thought:
                print(f"\n💡 思考: {thought}")

            if not action:
                # 格式容错回路:不直接放弃,把格式错误作为观察反馈给模型自我纠正
                print("警告:未能解析出有效的Action,已反馈给模型要求修正格式。")
                self.history.append(f"(系统提示:你上一轮的输出没有可解析的 Action,请严格按 Thought:/Action: 格式重新输出)")
                continue

            # 4. 判断开头是否为 Finish 指令
            if action.startswith("Finish"):
                final_answer = self._parse_action(action)[1]
                if not final_answer:   # Finish[] 解析失败时兜底,取括号后全部内容
                    final_answer = action[len("Finish"):].lstrip("[").rstrip("]") or "(未能提取到答案内容)"
                print(f"\n🎉 最终答案: {final_answer}")
                return final_answer

            # 5. 解析工具名与输入并执行
            tool_name, tool_input = self._parse_action(action)
            if not tool_name:
                # 同样走容错回路:格式问题反馈回历史
                print("警告:Action格式无效,已反馈给模型要求修正格式。")
                self.history.append(f"Action: {action}")
                self.history.append(f"Observation: (系统提示:Action 格式无效,必须形如 工具名[输入] 或 Finish[答案],请重新输出)")
                continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")

            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                # 工具不存在也要写入观察,让模型知道该换工具而不是反复重试
                observation = f"错误:未找到名为 '{tool_name}' 的工具,可用工具请看提示词中的列表。"
            else:
                observation = tool_function(tool_input)  # 调用真实工具

            print(f"👀 观察: {observation}")

            # 6. 将本轮 Thought/Action/Observation 添加到历史记录(保留思考链)
            self.history.append(f"Thought: {thought}")
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        # 循环结束仍未 Finish:强制模型基于已有历史总结答案,而不是直接放弃
        return self._force_final_answer(question)

    def _parse_output(self, text: str) -> tuple[str | None, str | None]:
        '''用正则从 LLM 输出中提取 Thought 和 Action,解析失败的项为 None。'''
        # Thought: 匹配到 Action: 或文本末尾
        #re.search 表示从头开始扫，r表示原始字符串（防止被转义）
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        # Action: 匹配到文本末尾
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self, action_text: str) -> tuple[str | None, str | None]:
        '''解析 Action 字符串,提取工具名和输入,兼容 Finish[答案] 格式。'''
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None

    def _force_final_answer(self, question: str) -> str:
        '''达到最大步数后禁止调用工具,强制 LLM 基于已有历史总结最终答案。'''
        print("\n已达到最大步数,强制总结答案...")
        history_str = "\n".join(self.history) if self.history else "(空)"
        prompt = FINAL_ANSWER_PROMPT_TEMPLATE.format(question=question, history=history_str)
        messages = [{"role": "user", "content": prompt}]
        final_answer = self.llm_client.think(messages=messages)
        if final_answer:
            print(f"\n🎉 最终答案(强制总结): {final_answer}")
        return final_answer
