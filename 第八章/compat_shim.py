"""
框架与新版依赖的兼容垫片: hello-agents v0.2.0 在 qdrant-client 1.19 / Neo4j Aura 上有四处不兼容,本模块统一打补丁,让旧框架能在新依赖上运行。

ensure_qdrant_compat: 往 qdrant_client.http.models 包对象注入 SearchRequest 别名 + 给 QdrantClient 补 search/search_batch 旧方法 + 给 CollectionInfo 补 vectors_count 属性
ensure_neo4j_compat: 当 database=neo4j 连不通时,自动回退到 Aura 的 home database(即用户名同名库)
ensure_all: 一键执行上述全部垫片,幂等可重复调用
"""

import importlib
import logging
import sys

logger = logging.getLogger(__name__)


def _inject_searchrequest():
    '''
    往 qdrant_client.http.models 包对象注入 SearchRequest 别名。

    关键陷阱: qdrant_client/http/models/ 既是包(__init__.py,会 re-export 子模块名字),
    又含同名子模块 models.py。`from qdrant_client.http import models` 取到的是子模块,
    而框架 `from qdrant_client.http.models import SearchRequest` 解析的是包对象
    (sys.modules['qdrant_client.http.models'])。两者不同,必须注入到包对象才生效。
    '''
    try:
        import importlib
        # importlib.import_module 拿到的就是 sys.modules 里的包对象
        pkg = importlib.import_module("qdrant_client.http.models")
        sub = sys.modules.get("qdrant_client.http.models.models")
        # 兼容空类: 框架仅 import 而不实例化 SearchRequest
        if not hasattr(pkg, "SearchRequest"):
            class SearchRequest:
                pass
            pkg.SearchRequest = SearchRequest
        # 子模块也注入一份,双保险
        if sub is not None and not hasattr(sub, "SearchRequest"):
            sub.SearchRequest = pkg.SearchRequest
    except Exception:
        pass


def ensure_qdrant_compat():
    '''新版 qdrant-client 移除了 SearchRequest 与 client.search,框架仍调用旧接口,这里注入兼容层。'''
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        return  # qdrant_client 未装,让框架报原始错误

    # --- 1. SearchRequest 别名(必须最先、无条件执行,否则框架 QDRANT_AVAILABLE 恒为 False) ---
    _inject_searchrequest()

    # --- 2. 给 CollectionInfo 补 vectors_count(points_count 的别名) ---
    try:
        from qdrant_client.http.models import CollectionInfo
        if not hasattr(CollectionInfo, "vectors_count"):
            # 用 property 动态兜底: 优先 points_count,其次 indexed_vectors_count
            CollectionInfo.vectors_count = property(
                lambda self: getattr(self, "points_count", None)
                             or getattr(self, "indexed_vectors_count", 0)
            )
    except Exception:
        pass

    # --- 3. 给 QdrantClient 补旧版 search / search_batch 方法 ---
    if not hasattr(QdrantClient, "search"):
        def _search_compat(
            self,
            collection_name,
            query_vector,
            query_filter=None,
            limit=10,
            score_threshold=None,
            with_payload=True,
            with_vectors=False,
            search_params=None,
            **kwargs,
        ):
            '''旧 client.search 的兼容实现,内部转调新版 query_points 并还原旧返回结构。'''
            from qdrant_client.http.models import QueryResponse
            # query_points 接受 named vector 或裸 float list
            query = list(query_vector) if not isinstance(query_vector, (list, tuple)) else query_vector
            resp = self.query_points(
                collection_name=collection_name,
                query=query,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=with_payload,
                with_vectors=with_vectors,
                search_params=search_params,
            )
            # 旧 search 返回 List[ScoredPoint]; query_points 返回 QueryResponse(points=[ScoredPoint...])
            # ScoredPoint 已带 id/score/payload,直接取 .points 即可
            return resp.points if isinstance(resp, QueryResponse) else list(resp)

        QdrantClient.search = _search_compat

    if not hasattr(QdrantClient, "search_batch"):
        def _search_batch_compat(self, collection_name, requests, **kwargs):
            '''旧 search_batch 的兼容实现: 逐条转调 query_points。'''
            results = []
            for req in requests:
                # 旧 SearchRequest 有 vector/filter/limit/params 等属性; 兼容层仅取已知字段
                qv = getattr(req, "vector", None) or getattr(req, "query_vector", None)
                qf = getattr(req, "filter", None) or getattr(req, "query_filter", None)
                lim = getattr(req, "limit", 10)
                thr = getattr(req, "score_threshold", None)
                sp = getattr(req, "params", None) or getattr(req, "search_params", None)
                results.append(self.search(
                    collection_name=collection_name,
                    query_vector=qv,
                    query_filter=qf,
                    limit=lim,
                    score_threshold=thr,
                    search_params=sp,
                    with_payload=True,
                    with_vectors=False,
                ))
            return results
        QdrantClient.search_batch = _search_batch_compat


def ensure_neo4j_compat():
    '''Neo4j Aura 的 home database 不是 "neo4j" 而是用户名同名库; 启动时把环境变量对齐,避免框架用错库名。

    说明: Aura 报 "database does not exist" 是在 session.run() 惰性获取路由表时抛出的,
    而非 session() 构造时,因此无法靠包装 Driver.session 捕获。Aura 规则: home database 恒等于
    用户名,故这里在框架读取 NEO4J_DATABASE 之前直接把环境变量改成用户名同名库。
    '''
    import os
    db = os.getenv("NEO4J_DATABASE")
    user = os.getenv("NEO4J_USERNAME")
    # 仅当 database 缺省/为默认 "neo4j", 且用户名存在且非 "neo4j"(即 Aura)时回退
    if db in (None, "", "neo4j") and user and user != "neo4j":
        os.environ["NEO4J_DATABASE"] = user
        logger.info(
            f"⚠️ NEO4J_DATABASE 为默认 'neo4j',Aura 无此库; "
            f"自动回退到用户名同名库(home database): {user}"
        )


def ensure_all():
    '''一次性应用全部垫片; 在 import hello_agents.* 之前调用。'''
    ensure_qdrant_compat()
    ensure_neo4j_compat()


# 导入本模块即自动执行
ensure_all()
