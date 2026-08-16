'''
工具的创建与管理: 向 ReAct 智能体提供可注册、可调用的外部工具。

ToolExecutor: 工具执行器,负责注册(registerTool)、按名获取(getTool)与列出可用工具(getAvailableTools)
search: SerpApi 网页搜索引擎工具,优先返回 answer_box/知识图谱等直接答案,否则退回前三条搜索摘要
'''

import os
from dotenv import load_dotenv
from serpapi import SerpApiClient

load_dotenv()   #加载.env环境变量,必须在读取os.getenv之前执行
def search(query: str) -> str:
    '''基于 SerpApi 的网页搜索工具,智能解析优先返回直接答案或知识图谱。'''
    print(f"正在执行[SerpApi]网页搜索：{query}")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")   #键名要与.env里的SERPAPI_API_KEY完全一致(原代码误写成SERPAPI_PI_KEY)
        if not api_key:
            return "错误:SERPAPI_API_KEY未在.env文件中配置。"
        #params一般表示参数
        params = {
            "engine":"google",
            "q":query,
            "api_key":api_key,
            "gl":"cn",  #国家代码
            "hl":"zh-cn",   #语言代码(中文是zh不是zn)
        }
        #创建一个客户端实例对象
        client = SerpApiClient(params)
        results = client.get_dict()     #将接口返回的json转换成python字典

        #智能解析:优先寻找最直接的答案,下面if后面的字段名都是SerpApi服务商规定好的标准结构
        if "answer_box_list" in results:
            #answer_box_list的每个元素是字典而非字符串,join前先从每个字典取出answer/snippet字段
            answers = [box.get("answer") or box.get("snippet") or "" for box in results["answer_box_list"]]
            return "\n".join(answers)
        if "answer_box" in results and "answer" in results["answer_box"]:
            return results["answer_box"]["answer"]
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            return results["knowledge_graph"]["description"]
        if "organic_results" in results and results["organic_results"]:
            # 如果没有直接答案，则返回前三个有机结果的摘要
            #[ 表达式  for 变量 in 可迭代对象 ] 每执行一次for in 就赋值给前面的表达式
            #注意:organic_results里第一条常常是广告或旧页面(如上面的RTX 30对比页),时效性问题建议多看几条结果
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
        self.tools: dict[str, dict[str, Any]] = {}  #相当于name,{description,func},自动生成空字典
    #callable在需要返回计算结果以及报错时使用，无需的时候用runnable
    def registerTool(self, name: str, description: str, func: callable):
        """
        向工具箱中注册一个新工具。
        """
        if name in self.tools:  #判断是否存在key
            print(f"警告:工具 '{name}' 已存在，将被覆盖。")
        self.tools[name] = {"description": description, "func": func}
        print(f"工具 '{name}' 已注册。")

    def getTool(self, name: str) -> callable:   #callable根据名称返回了search这个执行函数
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


# --- 工具初始化与使用示例 ---
if __name__ == '__main__':
    # 1. 初始化工具执行器
    toolExecutor = ToolExecutor()

    # 2. 注册我们的实战搜索工具
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    toolExecutor.registerTool("Search", search_description, search)
    
    # 3. 打印可用的工具
    print("\n--- 可用的工具 ---")
    print(toolExecutor.getAvailableTools())

    # 4. 智能体的Action调用，这次我们问一个实时性的问题
    print("\n--- 执行 Action: Search['英伟达最新的GPU型号是什么'] ---")
    tool_name = "Search"
    tool_input = "英伟达最新的GPU型号是什么"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input)
        print("--- 观察 (Observation) ---")
        print(observation)
    else:
        print(f"错误:未找到名为 '{tool_name}' 的工具。")
