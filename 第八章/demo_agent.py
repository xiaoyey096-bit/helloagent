"""
智能体演示: 用 SimpleAgent 展示记忆与检索如何增强一个对话智能体,对比基线与增强后的回答质量。

create_memory_tool: 构造启用 working/semantic 的 MemoryTool(演示记忆增强用)
create_rag_tool: 构造 RAGTool(演示检索增强用,知识库与 demo_rag 共用)
create_agent: 构造无工具的基线 SimpleAgent,作为对照
demo_baseline: 展示无任何增强的 SimpleAgent 基线对话
demo_memory_enhanced: 先写入用户偏好记忆,再查回并注入 prompt,展示记忆增强
demo_rag_enhanced: 用 RAG 检索知识片段注入 prompt,展示检索增强
demo_combined: 记忆 + 检索联合注入 prompt,展示完整的记忆与检索增强智能体
main: 串联上述步骤,用同一 agent 保持多轮上下文
"""

import os
import sys

# Windows 控制台默认 GBK 编码,打印 emoji 会抛 UnicodeEncodeError,这里强制 UTF-8 输出
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

# 加载 .env(会从本目录向上逐级查找项目根 .env)
load_dotenv()

# 垫片: 新版 qdrant-client 移除了框架 import 的 SearchRequest,会导致框架误报
# "qdrant-client未安装";必须先注入兼容别名,再 import 任何 hello_agents 模块
import compat_shim  # noqa: F401

from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.agents.simple_agent import SimpleAgent
from hello_agents.tools.builtin.memory_tool import MemoryTool
from hello_agents.tools.builtin.rag_tool import RAGTool


# ==================== 工具与智能体构造 ====================

def create_memory_tool(user_id: str = "agent_user") -> MemoryTool:
    '''构造启用 working/semantic 两类记忆的 MemoryTool,用独立 user_id 与 demo_memory 隔离。'''
    return MemoryTool(
        user_id=user_id,
        memory_types=["working", "semantic"],
    )


def create_rag_tool(namespace: str = "default") -> RAGTool:
    '''构造 RAGTool,与 demo_rag 共用同一知识库集合 rag_knowledge_base。'''
    kb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")
    return RAGTool(
        knowledge_base_path=kb_path,
        collection_name="rag_knowledge_base",
        rag_namespace=namespace,
    )


def create_agent() -> SimpleAgent:
    '''构造无工具的基线 SimpleAgent,system_prompt 定位为"记忆与检索增强助手"。'''
    llm = HelloAgentsLLM()
    system_prompt = (
        "你是一个记忆与检索增强的智能助手。"
        "回答时:若提供了【已知记忆】或【检索知识】,请优先基于这些信息作答,"
        "并在回答末尾用一句话说明本次回答用到了哪类增强(记忆/检索/两者)。"
        "回答保持简洁,使用中文。"
    )
    return SimpleAgent(
        name="memory_rag_agent",
        llm=llm,
        system_prompt=system_prompt,
        enable_tool_calling=False,  # 基线先关闭工具,手动编排增强流程
    )


# ==================== 演示一:基线对话 ====================

def demo_baseline(agent: SimpleAgent):
    '''展示无任何外部增强的 SimpleAgent 基线对话能力。'''
    print("\n" + "=" * 50)
    print("🗣️ 演示一: 基线对话(无记忆/检索增强)")
    print("=" * 50)

    print("\n👤 用户: 你好,请用一句话介绍你自己。")
    print(f"🤖 助手: {agent.run('你好,请用一句话介绍你自己。')}")


# ==================== 演示二:记忆增强 ====================

def demo_memory_enhanced(agent: SimpleAgent, memory_tool: MemoryTool):
    '''先写入一条用户偏好记忆,再查回并注入 prompt,展示记忆如何增强回答。'''
    print("\n" + "=" * 50)
    print("🧠 演示二: 记忆增强(写入→检索→注入)")
    print("=" * 50)

    # 1. 写入一条用户偏好到语义记忆
    print("\n--- 写入用户偏好到记忆 ---")
    print(memory_tool.run({
        "action": "add",
        "content": "用户是 Datawhale 的学习者,偏好用中文、简洁地回答,正在学智能体记忆与检索",
        "memory_type": "semantic",
        "importance": 0.9,
    }))

    # 2. 语义检索查回偏好
    print("\n--- 检索相关记忆 ---")
    mem_result = memory_tool.run({
        "action": "search",
        "query": "用户偏好",
        "limit": 2,
    })
    print(mem_result)

    # 3. 把记忆注入 prompt,让 agent 基于记忆回答
    print("\n--- 注入记忆后让 agent 回答 ---")
    enhanced_input = (
        f"【已知记忆】\n{mem_result}\n\n"
        "用户问题: 你记得关于我的什么信息?请基于记忆回答。"
    )
    print(f"👤 用户: {enhanced_input}")
    print(f"🤖 助手: {agent.run(enhanced_input)}")


# ==================== 演示三:检索增强 ====================

def demo_rag_enhanced(agent: SimpleAgent, rag_tool: RAGTool):
    '''用 RAG 检索知识片段注入 prompt,展示检索如何增强回答(普通检索,避免高级检索的长耗时)。'''
    print("\n" + "=" * 50)
    print("📚 演示三: 检索增强(RAG 检索→注入)")
    print("=" * 50)

    # 1. 确保知识库有内容(幂等写入一条,与 demo_rag 共用集合)
    print("\n--- 确保知识库有可检索内容 ---")
    print(rag_tool.run({
        "action": "add_text",
        "text": "智能体的记忆生命周期包括:编码、存储、检索、整合、遗忘五个阶段。",
        "document_id": "concept_memory_lifecycle",
    }))

    # 2. 检索知识片段(用普通检索,快)
    print("\n--- 检索知识片段 ---")
    rag_result = rag_tool.run({
        "action": "search",
        "query": "记忆的生命周期",
        "limit": 3,
        "enable_advanced_search": False,
    })
    print(rag_result)

    # 3. 注入 prompt 让 agent 基于知识回答
    print("\n--- 注入知识后让 agent 回答 ---")
    enhanced_input = (
        f"【检索知识】\n{rag_result}\n\n"
        "用户问题: 智能体记忆的生命周期包括哪些阶段?请基于检索知识回答。"
    )
    print(f"👤 用户: 智能体记忆的生命周期包括哪些阶段?")
    print(f"🤖 助手: {agent.run(enhanced_input)}")


# ==================== 演示四:联合增强 ====================

def demo_combined(agent: SimpleAgent, memory_tool: MemoryTool, rag_tool: RAGTool):
    '''记忆 + 检索联合注入 prompt,展示完整的记忆与检索增强智能体。'''
    print("\n" + "=" * 50)
    print("🔗 演示四: 记忆 + 检索联合增强")
    print("=" * 50)

    # 同时检索记忆与知识
    print("\n--- 同时检索记忆与知识 ---")
    mem_result = memory_tool.run({
        "action": "search",
        "query": "用户",
        "limit": 2,
    })
    rag_result = rag_tool.run({
        "action": "search",
        "query": "记忆类型 工作记忆 情景记忆",
        "limit": 3,
        "enable_advanced_search": False,
    })
    print("【记忆】:", mem_result[:150], "...")
    print("【知识】:", rag_result[:150], "...")

    # 双重注入
    print("\n--- 记忆+知识联合注入后让 agent 回答 ---")
    enhanced_input = (
        f"【已知记忆】\n{mem_result}\n\n"
        f"【检索知识】\n{rag_result}\n\n"
        "用户问题: 结合你记得的我的背景和检索到的知识,"
        "给我讲讲智能体的记忆有哪几种类型,以及这些和我学的有什么关系。"
    )
    print(f"👤 用户: 结合记忆和知识,讲讲智能体记忆类型,以及和我的关系。")
    print(f"🤖 助手: {agent.run(enhanced_input)}")


# ==================== 主入口 ====================

def main():
    '''串联:基线 → 记忆增强 → 检索增强 → 联合增强,用同一 agent 保持多轮上下文。'''
    print("🚀 第八章 · 记忆与检索增强智能体演示\n")

    # 构造工具与智能体
    memory_tool = create_memory_tool()
    rag_tool = create_rag_tool()
    agent = create_agent()

    # 依次演示(同一 agent,累积多轮对话上下文)
    demo_baseline(agent)
    demo_memory_enhanced(agent, memory_tool)
    demo_rag_enhanced(agent, rag_tool)
    demo_combined(agent, memory_tool, rag_tool)

    print("\n" + "=" * 50)
    print("✅ 智能体演示完成!")
    print("=" * 50)
    print("\n💡 关键要点:")
    print("  • 基线 agent: 无外部信息,只能靠模型自身知识回答")
    print("  • 记忆增强: 先写入/检索记忆,注入 prompt,让 agent 个性化作答")
    print("  • 检索增强: 先 RAG 检索知识,注入 prompt,让 agent 基于事实作答")
    print("  • 联合增强: 记忆(你是谁)+ 检索(知识库)同时注入,最完整的增强")
    print("  • SimpleAgent 还支持 ToolRegistry 自主工具调用([TOOL_CALL] 格式),")
    print("    此处聚焦记忆与检索的增强机制,自主调用见 simple_agent.py")


if __name__ == "__main__":
    main()
