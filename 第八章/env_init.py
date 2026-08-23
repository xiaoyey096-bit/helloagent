"""
环境初始化与连接自检: 逐一验证 .env 中 LLM / Embedding / Qdrant / Neo4j 四项服务的连通性,并给出向量维度对齐提示。

check_env: 读取并展示 .env 关键变量,缺项即提前报错
check_llm: 用 HelloAgentsLLM.invoke 发一句话请求,验证 LLM 可用
check_embedding: 用 get_text_embedder 探测实际向量维度,确认与 Qdrant 集合维度一致
check_qdrant: 用 qdrant_client 连接云服务并列出现有集合,提示旧集合需删除以重建为 768 维
check_neo4j: 用 neo4j.GraphDatabase.driver 跑一句 RETURN 1,验证图数据库连通
main: 依次跑上述四项,打印汇总表
"""

import os
import sys

# Windows 控制台默认 GBK 编码,打印 emoji 会抛 UnicodeEncodeError,这里强制 UTF-8 输出
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

# 加载 .env(会从本目录向上逐级查找项目根 .env)
load_dotenv()


# ==================== 配置检查 ====================

def check_env() -> bool:
    '''读取并打印 .env 关键变量,缺关键项返回 False。'''
    print("\n" + "=" * 50)
    print("📋 环境变量检查")
    print("=" * 50)

    required = {
        "LLM": ["LLM_API_KEY", "LLM_MODEL_ID", "LLM_BASE_URL"],
        "Embedding": ["EMBED_API_KEY", "EMBED_MODEL_NAME", "EMBED_BASE_URL", "EMBED_MODEL_TYPE"],
        "Qdrant": ["QDRANT_URL", "QDRANT_API_KEY"],
        "Neo4j": ["NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"],
    }

    all_ok = True
    for service, keys in required.items():
        print(f"\n[{service}]")
        for k in keys:
            v = os.getenv(k)
            if v:
                # 只显示前 25 字符,避免泄露密钥
                shown = v[:25] + "..." if len(v) > 25 else v
                print(f"  ✅ {k} = {shown}")
            else:
                print(f"  ❌ {k} 未设置")
                all_ok = False

    return all_ok


# ==================== LLM 检查 ====================

def check_llm() -> bool:
    '''调用 HelloAgentsLLM.invoke 发一句话,验证 LLM 连通。'''
    print("\n" + "=" * 50)
    print("🤖 LLM 连接检查")
    print("=" * 50)
    try:
        from hello_agents.core.llm import HelloAgentsLLM
        llm = HelloAgentsLLM()
        resp = llm.invoke([
            {"role": "system", "content": "你是测试助手。"},
            {"role": "user", "content": "只回复两个字:在吗"},
        ])
        if resp and "在吗" in resp:
            print(f"  ✅ LLM 可用,返回: {resp.strip()}")
            return True
        print(f"  ⚠️ LLM 返回异常: {repr(resp)[:100]}")
        return False
    except Exception as e:
        print(f"  ❌ LLM 连接失败: {e}")
        return False


# ==================== Embedding 检查 ====================

def check_embedding() -> bool:
    '''探测 embedding 实际向量维度,确认与 Qdrant 集合维度一致。'''
    print("\n" + "=" * 50)
    print("🔢 Embedding 连接检查")
    print("=" * 50)
    try:
        from hello_agents.memory.embedding import get_text_embedder, get_dimension
        embedder = get_text_embedder()
        actual_dim = embedder.dimension
        env_dim = os.getenv("QDRANT_VECTOR_SIZE", "384")

        print(f"  模型: {embedder.model_name}")
        print(f"  实际向量维度: {actual_dim}")
        print(f"  .env 中 QDRANT_VECTOR_SIZE: {env_dim}")

        if str(actual_dim) != str(env_dim):
            print(f"  ⚠️ 维度不一致!实际 {actual_dim} ≠ 配置 {env_dim}")
            print(f"     框架按实际维度 {actual_dim} 创建集合,旧集合若为 {env_dim} 维需删除重建")
        else:
            print(f"  ✅ 维度对齐: {actual_dim}")

        # 发一句真实请求验证连通
        vec = embedder.encode("连接测试")
        print(f"  ✅ Embedding 可用,返回向量长度: {len(vec)}")
        return True
    except Exception as e:
        print(f"  ❌ Embedding 连接失败: {e}")
        return False


# ==================== Qdrant 检查 ====================

def check_qdrant() -> bool:
    '''连接 Qdrant 云并列出现有集合,提示旧维度集合需删除。'''
    print("\n" + "=" * 50)
    print("📦 Qdrant 向量数据库检查")
    print("=" * 50)
    try:
        from qdrant_client import QdrantClient
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        client = QdrantClient(url=url, api_key=api_key, timeout=30)

        collections = client.get_collections()
        print(f"  ✅ Qdrant 连接成功")
        print(f"  现有集合:")
        if not collections.collections:
            print("    (空,首次运行时框架会自动创建)")
        for c in collections.collections:
            try:
                info = client.get_collection(c.name)
                dim = info.config.params.vectors.size
                print(f"    • {c.name} (维度: {dim}, 点数: {info.points_count})")
            except Exception:
                print(f"    • {c.name} (无法读取详情)")

        return True
    except Exception as e:
        print(f"  ❌ Qdrant 连接失败: {e}")
        return False


# ==================== Neo4j 检查 ====================

def check_neo4j() -> bool:
    '''连接 Neo4j Aura 并跑一句 RETURN 1 验证连通。'''
    print("\n" + "=" * 50)
    print("🕸️  Neo4j 图数据库检查")
    print("=" * 50)
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        pwd = os.getenv("NEO4J_PASSWORD")
        driver = GraphDatabase.driver(uri, auth=(user, pwd))

        with driver.session() as session:
            result = session.run("RETURN 1 AS n")
            record = result.single()
            print(f"  ✅ Neo4j 连接成功,RETURN 1 → {record['n']}")

        driver.close()
        return True
    except Exception as e:
        print(f"  ❌ Neo4j 连接失败: {e}")
        return False


# ==================== 主入口 ====================

def main():
    '''依次跑四项自检并打印汇总。'''
    print("\n🚀 开始第八章环境自检...\n")

    results = {
        "环境变量": check_env(),
        "LLM": check_llm(),
        "Embedding": check_embedding(),
        "Qdrant": check_qdrant(),
        "Neo4j": check_neo4j(),
    }

    print("\n" + "=" * 50)
    print("📊 自检汇总")
    print("=" * 50)
    for name, ok in results.items():
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"  {name}: {status}")

    all_ok = all(results.values())
    print(f"\n{'🎉 所有检查通过!可以运行后续演示。' if all_ok else '⚠️ 部分检查未通过,请按提示修复。'}")
    return all_ok


if __name__ == "__main__":
    main()
