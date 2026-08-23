"""
RAG 检索增强生成演示: 用 RAGTool 完整走通文档加载→分块向量化→语义检索→智能问答四步流程。

create_rag_tool: 构造 RAGTool 实例,知识库指向 ./knowledge_base,集合用默认 rag_knowledge_base
demo_add_documents: 先用 add_text 写入两段知识点,再用 add_document 索引样例 Markdown 文档
demo_search: 对同一问题分别演示普通检索与高级检索(MQE+HyDE),对比召回效果
demo_ask: 走完 检索→上下文注入→LLM 生成 的完整 RAG 问答链路
demo_stats: 打印知识库向量数与存储统计
main: 串联上述步骤,完整演示一次 RAG 生命周期
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

from hello_agents.tools.builtin.rag_tool import RAGTool


# ==================== 工具构造 ====================

def create_rag_tool(namespace: str = "default") -> RAGTool:
    '''构造 RAGTool,知识库目录放在脚本同级 knowledge_base 下,集合复用默认 rag_knowledge_base。'''
    kb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")
    return RAGTool(
        knowledge_base_path=kb_path,
        collection_name="rag_knowledge_base",
        rag_namespace=namespace,
    )


# ==================== 添加文档 ====================

def demo_add_documents(rag_tool: RAGTool):
    '''先用 add_text 写入两段文本,再用 add_document 索引样例 Markdown,展示两种入库方式。'''
    print("\n" + "=" * 50)
    print("📚 演示一: 添加文档到知识库(add_text + add_document)")
    print("=" * 50)

    # --- add_text: 直接把一段文本写入知识库,内部会落临时 .md 再 MarkItDown 解析 ---
    print("\n--- add_text: 写入两段知识点 ---")
    print(rag_tool.run({
        "action": "add_text",
        "text": (
            "RAG 的检索阶段默认采用向量相似度检索,把用户问题与知识库中每个分块都转为向量,"
            "再按余弦相似度排序取 Top-K。"
        ),
        "document_id": "concept_vector_retrieval",
    }))
    print(rag_tool.run({
        "action": "add_text",
        "text": (
            "HyDE(假设文档嵌入)是一种高级检索技巧:先让 LLM 为问题生成一个假想答案,"
            "再用假想答案的向量去检索,从而更贴近答案所在的文档片段分布。"
        ),
        "document_id": "concept_hyde",
    }))

    # --- add_document: 索引一个真实的 Markdown 文件,走完整解析+分块+向量化 ---
    print("\n--- add_document: 索引样例文档 sample_knowledge.md ---")
    sample_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_knowledge.md")
    print(rag_tool.run({
        "action": "add_document",
        "file_path": sample_path,
    }))


# ==================== 语义检索 ====================

def demo_search(rag_tool: RAGTool):
    '''对同一问题分别演示普通检索与高级检索(MQE+HyDE),对比召回片段。'''
    print("\n" + "=" * 50)
    print("🔍 演示二: 语义检索(普通检索 vs 高级检索)")
    print("=" * 50)

    query = "记忆有哪几种类型?"

    print(f"\n🔎 查询: {query}")

    print("\n--- 普通检索(enable_advanced_search=False) ---")
    print(rag_tool.run({
        "action": "search",
        "query": query,
        "limit": 3,
        "enable_advanced_search": False,
    }))

    print("\n--- 高级检索(MQE 多查询扩展 + HyDE 假设文档嵌入) ---")
    print(rag_tool.run({
        "action": "search",
        "query": query,
        "limit": 3,
        "enable_advanced_search": True,
    }))


# ==================== 智能问答 ====================

def demo_ask(rag_tool: RAGTool):
    '''走完 检索→上下文注入→LLM 生成 的完整 RAG 问答链路。'''
    print("\n" + "=" * 50)
    print("🤖 演示三: 智能问答(检索增强生成)")
    print("=" * 50)

    questions = [
        "智能体的记忆系统分为哪几种类型?",
        "RAG 的标准流程是什么?",
        "HyDE 是什么,它解决了什么问题?",
    ]

    for q in questions:
        print(f"\n❓ 问题: {q}")
        print(rag_tool.run({
            "action": "ask",
            "question": q,
            "limit": 4,
        }))


# ==================== 知识库统计 ====================

def demo_stats(rag_tool: RAGTool):
    '''打印知识库向量数与存储统计。'''
    print("\n" + "=" * 50)
    print("📊 演示四: 知识库统计")
    print("=" * 50)

    print(rag_tool.run({"action": "stats"}))


# ==================== 主入口 ====================

def main():
    '''串联完整 RAG 流程: 添加文档 → 检索对比 → 智能问答 → 统计。'''
    print("🚀 第八章 · RAG 检索增强生成演示\n")

    rag_tool = create_rag_tool()

    # 依次演示
    demo_add_documents(rag_tool)
    demo_search(rag_tool)
    demo_ask(rag_tool)
    demo_stats(rag_tool)

    print("\n" + "=" * 50)
    print("✅ RAG 演示完成!")
    print("=" * 50)
    print("\n💡 关键要点:")
    print("  • add_text: 直接写入文本,适合临时/短知识")
    print("  • add_document: 索引文件,走 MarkItDown 解析 + 段落级分块")
    print("  • 普通检索: 纯向量相似度,快但召回窄")
    print("  • 高级检索: MQE 多查询扩展 + HyDE 假设文档,召回更全")
    print("  • ask: 检索 Top-K → 拼 context → LLM 生成 → 附引用来源")


if __name__ == "__main__":
    main()
