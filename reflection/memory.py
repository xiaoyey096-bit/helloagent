"""
短期记忆模块: 按时间顺序存储 Reflection 智能体的"执行-反思"轨迹,并可序列化为提示词上下文。

Memory: 短期记忆;add_record 追加 execution/reflection 记录,get_trajectory 把全部轨迹拼成连贯文本,get_last_execution 倒序取最新代码
"""

from typing import Any, Dict, List, Optional


class Memory:
    '''短期记忆:用列表按顺序存储行动与反思轨迹,供后续轮次构建提示词。'''

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def add_record(self, record_type: str, content: str):
        '''向记忆追加一条记录(record_type 为 execution 或 reflection)。'''
        self.records.append({"type": record_type, "content": content})
        print(f"📝 记忆已更新,新增一条 '{record_type}' 记录。")

    def get_trajectory(self) -> str:
        '''把全部轨迹序列化为连贯文本,可直接插入反思/优化提示词。'''
        trajectory_parts = []
        for record in self.records:
            if record['type'] == 'execution':
                trajectory_parts.append(f"--- 上一轮尝试 (代码) ---\n{record['content']}")
            elif record['type'] == 'reflection':
                trajectory_parts.append(f"--- 评审员反馈 ---\n{record['content']}")
        return "\n\n".join(trajectory_parts)

    def get_last_execution(self) -> Optional[str]:
        '''获取最近一次执行结果(最新代码),不存在返回 None。'''
        for record in reversed(self.records):
            if record['type'] == 'execution':
                return record['content']
        return None
