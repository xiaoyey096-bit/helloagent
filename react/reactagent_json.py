"""
JSON 版 ReAct 智能体: 用 JSON 结构化协议替代 Thought/Action 文本协议,解析层从正则改为 json.loads。

ReActJsonAgent: 与 ReActAgent 同一套循环;思考时直接请求接口的 json_object 模式(服务端保证合法 JSON),
_parse_output 做防御性解析(剥 markdown 围栏 → 截取首尾花括号 → json.loads → 字段校验),
工具名与输入直接来自 JSON 字段,不再需要 _parse_action 的二次正则;解析失败同样走历史反馈回路自纠
"""

import json
from llm import HelloAgentsLLM
from tools import ToolExecutor
from prompts_json import REACT_JSON_PROMPT_TEMPLATE, FINAL_ANSWER_PROMPT_TEMPLATE


class ReActJsonAgent:
    '''JSON 版 ReAct 智能体:llm_client 负责"思考"(JSON 模式),tool_executor 负责"行动",max_steps 防止无限循环。'''

    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []   # 每轮的 Thought/Action/Observation 文本记录(给模型读的可读形式)

    def run(self, question: str) -> str:
        '''运行 JSON 版 ReAct 主循环:每轮拿到结构化的 action_name/action_input,Finish 即返回,超步数强制总结。'''
        self.history = []  # 每次运行时重置历史记录
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n========== 第 {current_step} 步 ==========")

            # 1. 格式化提示词(工具描述 + 问题 + 历史)
            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history) if self.history else "(空)"
            prompt = REACT_JSON_PROMPT_TEMPLATE.format(
                tools=tools_desc,
                question=question,
                history=history_str
            )

            # 2. 调用 LLM 思考——关键差异:请求 json_object 模式,由服务端约束输出必须是合法 JSON
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(
                messages=messages,
                response_format={"type": "json_object"},
            )

            if not response_text:
                print("错误:LLM未能返回有效响应。")
                break

            # 3. 解析 JSON 输出(防线二/三:防御性解析 + 字段校验)
            thought, action_name, action_input = self._parse_output(response_text)

            if thought:
                print(f"\n💡 思考: {thought}")

            if not action_name:
                # 格式容错回路:不直接放弃,把解析错误作为观察反馈给模型自我纠正
                print("警告:未能解析出有效的Action,已反馈给模型要求修正格式。")
                self.history.append(f"(系统提示:你上一轮的输出不是合法 JSON 或缺少 action_name/action_input 字段,请只输出一个 JSON 对象)")
                continue

            # 4. Finish 则直接返回答案——JSON 字段天然分隔了"指令"与"内容",不需要正则二次拆解
            if action_name == "Finish":
                final_answer = action_input or "(未能提取到答案内容)"
                print(f"\n🎉 最终答案: {final_answer}")
                return final_answer

            # 5. 按 JSON 字段直接取工具名与输入并执行
            print(f"\n🎬 行动: {action_name}[{action_input}]")

            tool_function = self.tool_executor.getTool(action_name)
            if not tool_function:
                # 工具不存在也要写入观察,让模型知道该换工具而不是反复重试
                observation = f"错误:未找到名为 '{action_name}' 的工具,可用工具请看提示词中的列表。"
            else:
                observation = tool_function(action_input)  # 调用真实工具

            print(f"👀 观察: {observation}")

            # 6. 将本轮结果添加到历史记录(保留思考链,给模型读的仍是可读文本)
            self.history.append(f"Thought: {thought}")
            self.history.append(f"Action: {action_name}[{action_input}]")
            self.history.append(f"Observation: {observation}")

        # 循环结束仍未 Finish:强制模型基于已有历史总结答案
        return self._force_final_answer(question)

    def _parse_output(self, text: str) -> tuple[str | None, str | None, str | None]:
        '''防御性解析 JSON:剥围栏 → 截取首尾花括号 → json.loads → 字段校验,任一步失败返回 (None, None, None)。'''
        try:
            cleaned = text.strip()

            # 防线A:模型可能仍用 ```json ... ``` 包裹(json_object 未生效或被绕过时)
            if "```" in cleaned:
                parts = cleaned.split("```")
                cleaned = max(parts, key=len).strip()  # 取最长的一段,通常就是 JSON 主体
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()

            # 防线B:截取第一个 { 到最后一个 },丢弃前后混杂的解释文字
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None, None, None
            obj = json.loads(cleaned[start:end + 1])

            # 防线C:字段校验——action_name 必须是非空字符串;thought/action_input 缺省时容忍
            action_name = obj.get("action_name")
            if not isinstance(action_name, str) or not action_name.strip():
                return None, None, None
            thought = obj.get("thought")
            action_input = obj.get("action_input") or ""
            return (
                thought.strip() if isinstance(thought, str) else None,
                action_name.strip(),
                str(action_input).strip(),
            )
        except (json.JSONDecodeError, AttributeError, TypeError):
            return None, None, None

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
