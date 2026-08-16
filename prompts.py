"""
ReAct 智能体的提示词模板。

功能: 集中管理 ReAct 框架的系统提示词,规定 Thought/Action/Observation 的输出格式,供 reactagent.py 填充使用。
创建日期: 2026-08-15

输入: 无(纯模板;{tools}/{question}/{history} 三个占位符由 ReActAgent.run() 用 str.format 填充)
输出: ① REACT_PROMPT_TEMPLATE — ReAct 主循环提示词模板
      ② FINAL_ANSWER_PROMPT_TEMPLATE — 达到最大步数后强制总结答案的模板

注意: 模板中出现的字面大括号(如示例里的 tool_name[input])不含 { },若以后要加,必须写成 {{ }} 转义,
否则 str.format 会把它当成占位符报 KeyError。
"""

# ReAct 主循环提示词:告知可用工具、严格规定输出格式,并给出 few-shot 示例帮助小模型守格式
REACT_PROMPT_TEMPLATE = """你是一个能够调用外部工具的智能助手,请严格按照 ReAct 框架逐步推理并解决问题。

可用工具(只能从中选择,Action 中的工具名必须与下面完全一致):
{tools}

请严格按照以下格式回应(每次只输出一轮 Thought + Action):

Thought: 你的思考过程,分析问题、规划下一步行动。
Action: 二选一,格式如下:
- 调用工具: `工具名[工具输入]`,例如 `Search[英伟达最新GPU型号]`
- 给出最终答案: `Finish[你的最终答案]`

示例:
Thought: 这个问题需要最新的实时信息,我知识库里没有,应该先搜索。
Action: Search[英伟达最新GPU型号]

(系统会把工具结果作为 Observation 追加到下方历史记录中,你再进行下一轮思考。
收集到足够信息后必须用 Finish 结束,例如:)
Thought: 搜索结果已经给出答案,我现在可以回复用户了。
Action: Finish[英伟达最新的GPU是xxx]

规则:
1. Action 必须只有一行,且紧跟在 Thought 之后。
2. 不要自己编造 Observation,那是系统填入的。
3. 如果历史记录中提示你上轮格式有误,请严格按格式重新输出。

现在,请解决以下问题:

Question: {question}

历史记录(之前轮次的思考与观察,最新在最下方;为空表示这是第一轮):
{history}
"""

# 达到最大步数后的收尾提示词:禁止再调用工具,强制基于已有历史给出答案
FINAL_ANSWER_PROMPT_TEMPLATE = """你已经用完了可用的推理步数,不能再调用任何工具。
请仅根据下面的历史记录中已有的信息,直接给出对问题的最终回答;
如果信息不足,就诚实说明你目前掌握的内容和缺失的部分。

Question: {question}

历史记录:
{history}

请直接输出最终答案,不要使用任何 Action 格式。
"""
