"""
JSON 版 ReAct 提示词模板: 要求模型每轮只输出一个 JSON 对象,从协议层面消除格式歧义。

REACT_JSON_PROMPT_TEMPLATE: JSON 协议主模板,字段为 thought/action_name/action_input;示例 JSON 的花括号已用 {{}} 转义
FINAL_ANSWER_PROMPT_TEMPLATE: 达到最大步数后禁止调用工具、强制总结答案的模板(与文本版一致)
"""

# JSON 协议主模板:注意示例里的 {{ }} 是 .format() 的转义,实际发给模型的是单花括号
REACT_JSON_PROMPT_TEMPLATE = """你是一个能够调用外部工具的智能助手,请通过 ReAct 框架逐步推理并解决问题。

可用工具(action_name 只能从中选择,必须与下面完全一致):
{tools}

每一轮你必须只输出一个 JSON 对象,不要输出 JSON 以外的任何文字(包括 markdown 代码块、解释、注释)。格式:
{{"thought": "你的思考过程", "action_name": "工具名或Finish", "action_input": "工具输入或最终答案"}}

示例一(需要搜索):
{{"thought": "这个问题需要最新的实时信息,我知识库里没有,应该先搜索。", "action_name": "Search", "action_input": "英伟达最新GPU型号"}}

示例二(信息足够,直接收尾):
{{"thought": "搜索结果已经给出答案,我现在可以回复用户了。", "action_name": "Finish", "action_input": "英伟达最新的GPU是xxx"}}

规则:
1. action_name 为 Finish 时,action_input 填最终答案;为工具名时,action_input 填工具输入。
2. 不要自己编造 Observation,那是系统填入的。
3. 字符串值内部不要出现未转义的双引号与换行。
4. 如果历史记录提示你上轮格式有误,请严格按 JSON 格式重新输出。

现在,请解决以下问题:

Question: {question}

历史记录(之前轮次的思考与观察,最新在最下方;为空表示这是第一轮):
{history}
"""

# 达到最大步数后的收尾提示词:禁止再调用工具,强制基于已有历史给出答案(与文本版共用)
FINAL_ANSWER_PROMPT_TEMPLATE = """你已经用完了可用的推理步数,不能再调用任何工具。
请仅根据下面的历史记录中已有的信息,直接给出对问题的最终回答;
如果信息不足,就诚实说明你目前掌握的内容和缺失的部分。

Question: {question}

历史记录:
{history}

请直接输出最终答案,不要使用任何 Action 格式。
"""
