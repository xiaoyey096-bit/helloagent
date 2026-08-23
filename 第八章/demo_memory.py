"""
记忆系统演示: 用 MemoryTool 依次演示工作/情景/语义三类记忆的增删查、遗忘与整合生命周期。

create_memory_tool: 构造启用 working/episodic/semantic 的 MemoryTool 实例
demo_add_memories: 向三类记忆各写入若干条样本,展示重要性(importance)分级
demo_search_memories: 用语义检索在不同类型间召回相关记忆
demo_forget: 按重要性阈值遗忘低价值记忆,展示遗忘策略
demo_consolidate: 把重要的工作记忆整合为情景记忆(短期→长期)
demo_stats: 打印记忆系统统计与摘要
main: 串联上述步骤,完整演示一次记忆生命周期
"""

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

from hello_agents.tools.builtin.memory_tool import MemoryTool


# ==================== 工具构造 ====================

def create_memory_tool(user_id: str = "demo_user") -> MemoryTool:
    '''构造启用 working/episodic/semantic 三类记忆的 MemoryTool。'''
    return MemoryTool(
        user_id=user_id,
        memory_types=["working", "episodic", "semantic"],
    )


# ==================== 添加记忆 ====================

def demo_add_memories(memory_tool: MemoryTool):
    '''向三类记忆各写入样本,展示 importance 分级(0.0-1.0)。'''
    print("\n" + "=" * 50)
    print("📝 演示一: 添加记忆(工作/情景/语义三类)")
    print("=" * 50)

    # 工作记忆: 当前会话的临时信息,重要性分化(0.8 将被整合提升,0.5 将被遗忘)
    print("\n--- 工作记忆(当前会话临时信息) ---")
    print(memory_tool.run({
        "action": "add",
        "content": "用户正在学习 Datawhale hello-agents 教程的第八章",
        "memory_type": "working",
        "importance": 0.8,
    }))
    print(memory_tool.run({
        "action": "add",
        "content": "用户当前正在配置 Qdrant 和 Neo4j 云服务",
        "memory_type": "working",
        "importance": 0.5,
    }))

    # 情景记忆: 具体事件/交互,重要性较高
    print("\n--- 情景记忆(具体事件/交互) ---")
    print(memory_tool.run({
        "action": "add",
        "content": "今天成功跑通了讯飞星火 Qwen3-Embedding-8B,返回 768 维向量",
        "memory_type": "episodic",
        "importance": 0.8,
    }))
    print(memory_tool.run({
        "action": "add",
        "content": "调试时发现框架不读 QDRANT_VECTOR_SIZE,向量维度由 get_dimension() 探测决定",
        "memory_type": "episodic",
        "importance": 0.7,
    }))

    # 语义记忆: 通用知识/事实,重要性最高
    print("\n--- 语义记忆(通用知识/事实) ---")
    print(memory_tool.run({
        "action": "add",
        "content": "Qdrant 是开源的向量数据库,支持 HNSW 索引和余弦相似度检索",
        "memory_type": "semantic",
        "importance": 0.9,
    }))
    print(memory_tool.run({
        "action": "add",
        "content": "RAG = Retrieval-Augmented Generation,通过检索外部知识增强生成质量",
        "memory_type": "semantic",
        "importance": 0.9,
    }))


# ==================== 搜索记忆 ====================

def demo_search_memories(memory_tool: MemoryTool):
    '''用语义检索在不同类型间召回相关记忆。'''
    print("\n" + "=" * 50)
    print("🔍 演示二: 搜索记忆(语义向量召回)")
    print("=" * 50)

    queries = [
        ("向量数据库是什么?", None),              # 跨所有类型搜索
        ("用户在学什么教程?", None),               # 命中工作记忆
        ("今天发生了什么事?", ["episodic"]),       # 只搜情景记忆
        ("RAG 是什么?", ["semantic"]),             # 只搜语义记忆
    ]

    for query, mtype in queries:
        print(f"\n🔎 查询: {query}")
        params = {"action": "search", "query": query, "limit": 3}
        if mtype:
            params["memory_type"] = mtype[0]
        print(memory_tool.run(params))


# ==================== 遗忘策略 ====================

def demo_forget(memory_tool: MemoryTool):
    '''按重要性阈值遗忘低价值记忆。'''
    print("\n" + "=" * 50)
    print("🧹 演示三: 遗忘记忆(按重要性阈值)")
    print("=" * 50)

    print("\n遗忘前统计:")
    print(memory_tool.run({"action": "stats"}))

    # importance_based: 遗忘 importance < 0.55 的记忆
    print("\n执行遗忘(importance_based, threshold=0.55):")
    print(memory_tool.run({
        "action": "forget",
        "strategy": "importance_based",
        "threshold": 0.55,
    }))

    print("\n遗忘后统计:")
    print(memory_tool.run({"action": "stats"}))


# ==================== 记忆整合 ====================

def demo_consolidate(memory_tool: MemoryTool):
    '''把重要的工作记忆整合为情景记忆(短期→长期)。'''
    print("\n" + "=" * 50)
    print("🔄 演示四: 整合记忆(工作→情景,短期→长期)")
    print("=" * 50)

    print("\n整合前: 工作记忆中重要性 ≥ 0.7 的将被提升为情景记忆")
    print(memory_tool.run({"action": "stats"}))

    # consolidate: 把 from_type 中 importance ≥ threshold 的记忆转为 to_type
    print("\n执行整合(working → episodic, threshold=0.7):")
    print(memory_tool.run({
        "action": "consolidate",
        "from_type": "working",
        "to_type": "episodic",
        "importance_threshold": 0.7,
    }))

    print("\n整合后统计:")
    print(memory_tool.run({"action": "stats"}))


# ==================== 统计与摘要 ====================

def demo_stats(memory_tool: MemoryTool):
    '''打印记忆系统统计与摘要。'''
    print("\n" + "=" * 50)
    print("📊 演示五: 统计与摘要")
    print("=" * 50)

    print("\n--- 统计信息 ---")
    print(memory_tool.run({"action": "stats"}))

    print("\n--- 记忆摘要(含重要记忆 Top 5) ---")
    print(memory_tool.run({"action": "summary", "limit": 5}))


# ==================== 主入口 ====================

def main():
    '''串联完整记忆生命周期: 添加 → 搜索 → 遗忘 → 整合 → 统计。'''
    print("🚀 第八章 · 记忆系统演示\n")

    memory_tool = create_memory_tool()

    # 依次演示
    demo_add_memories(memory_tool)
    demo_search_memories(memory_tool)
    demo_forget(memory_tool)
    demo_consolidate(memory_tool)
    demo_stats(memory_tool)

    print("\n" + "=" * 50)
    print("✅ 记忆系统演示完成!")
    print("=" * 50)
    print("\n💡 关键要点:")
    print("  • 工作记忆(working): 短期临时,当前会话信息")
    print("  • 情景记忆(episodic): 具体事件与交互经历")
    print("  • 语义记忆(semantic): 通用知识与事实")
    print("  • forget: 按重要性/时间/容量策略遗忘")
    print("  • consolidate: 把重要的短期记忆提升为长期记忆")


if __name__ == "__main__":
    main()
