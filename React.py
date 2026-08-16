'''
涉及的语法：
.get(key,默认值【默认是None】)
enumerate(iterable,start = 0)作用：遍历可迭代对象，同时生成【索引，元素】，iterator 迭代器
[ 表达式  for 变量 in 可迭代对象 ] 每执行一次for in 就赋值给前面的表达式
'''

from serpapi import SerpApiClient
def search(query: str) -> str:
    '''
    一个基于SerpApi的实战网页搜索引擎工具。
    它会智能地解析搜索结果，优先返回直接答案或知识图谱信息。
    '''
    print(f"正在执行[SerpApi]网页搜索：{query}")
    try:
        api_key = os.getenv("SERPAPI_PI_KEY")
        if not api_key:
            return "错误:SERPAPI_API_KEY未在.env文件中配置。"
        #params一般表示参数
        params = {
            "engine":"google",
            "q":query,
            "api_key":api_key,
            "gl":"cn",  #国家代码
            "hl":"zn-cn",   #语言代码
        }
        #创建一个客户端实例对象
        client = SerpApiClient(params)
        results = client.get_dict()     #将接口返回的json转换成python字典

        #智能解析:优先寻找最直接的答案,下面if后面的字段名都是SerpApi服务商规定好的标准结构
        if "answer_box_list" in results:
            return "\n".join(results["answer_box_list"])
        if "answer_box" in results and "answer" in results["answer_box"]:
            return results["answer_box"]["answer"]
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            return results["knowledge_graph"]["description"]
        if "organic_results" in results and results["organic_results"]:
            # 如果没有直接答案，则返回前三个有机结果的摘要
            #[ 表达式  for 变量 in 可迭代对象 ] 每执行一次for in 就赋值给前面的表达式
            snippets = [
                f"[{i+1}] {res.get('title', '')}\n{res.get('snippet', '')}"
                for i, res in enumerate(results["organic_results"][:3])     #用for时自动调用迭代器内部方法，吐出(序号，字典)，(序号，字典)....
            ]
            return "\n\n".join(snippets)
        
        return f"对不起，没有找到关于 '{query}' 的信息。"

    except Exception as e:
        return f"搜索时发生错误: {e}"
        
#在上述代码中，首先会检查是否存在 answer_box（Google的答案摘要框）或 knowledge_graph（知识图谱）等信息，如果存在，就直接返回这些最精确的答案。如果不存在，它才会退而求其次，返回前三个常规搜索结果的摘要。这种“智能解析”能为LLM提供质量更高的信息输入。

from typing import Any
class ToolExecutor:
    """
    一个工具执行器，负责管理和执行工具。
    """
    def __init__(self):
        self.tools: dict[str, dict[str, Any]] = {}
    #callable在需要返回计算结果以及报错时使用，无需的时候用runnable
    def registerTool(self, name: str, description: str, func: callable):
        """
        向工具箱中注册一个新工具。
        """
        if name in self.tools:
            print(f"警告:工具 '{name}' 已存在，将被覆盖。")
        self.tools[name] = {"description": description, "func": func}
        print(f"工具 '{name}' 已注册。")

    def getTool(self, name: str) -> callable:
        """
        根据名称获取一个工具的执行函数。
        """
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串。
        """
        return "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.tools.items()
        ])
