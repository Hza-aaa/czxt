import json
import time
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable

from config import get_settings
from memory import ChatMemory
from tools import read_file, list_directory, get_file_info
from tools.code_tools import extract_code_structure, get_function_signatures


SYSTEM_PROMPT_TEMPLATE = """你是一个专业的代码解释助手 CodeExplainerAgent。你的任务是帮助用户理解代码逻辑、生成代码注释、回答代码相关问题。

## 核心能力
1. **代码解释**: 逐行或逐段解释代码功能、算法逻辑和设计意图
2. **代码注释生成**: 为代码生成清晰、规范的中文注释
3. **问题回答**: 回答关于代码实现、调用关系、依赖关系等问题
4. **结构分析**: 分析代码结构，提取函数、类、模块关系

## 工具使用规则
当需要查看文件内容、分析代码结构或浏览目录时，请**优先使用工具**获取信息，不要凭空猜测。

你可以通过以下格式调用工具（每次只调用一个工具）：

```tool_call
{{"tool": "工具名称", "parameters": {参数键值对}}}
```

## 可用工具列表
| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `read_file` | 读取代码文件内容，支持按行号范围读取 | `file_path` (必填): 文件路径; `start_line` (可选): 起始行; `end_line` (可选): 结束行 |
| `list_directory` | 列出目录下的文件和子目录 | `dir_path` (必填): 目录路径; `show_hidden` (可选): 是否显示隐藏文件 |
| `get_file_info` | 获取文件基本信息（大小、行数、语言类型等） | `file_path` (必填): 文件路径 |
| `extract_code_structure` | 分析代码结构，提取函数、类、导入、注释 | `code` (必填): 代码字符串; `language` (可选): 编程语言 |
| `get_function_signatures` | 提取所有函数/方法签名 | `code` (必填): 代码字符串; `language` (可选): 编程语言 |

## 响应格式
- 如果需要调用工具: 只输出工具调用块，不要加其他内容
- 如果直接回答: 输出清晰的中文回答，代码部分用 Markdown 代码块标记
- 回答要具体、专业、有条理，必要时配合代码示例和流程说明
- 回答时引用代码行号，格式如 `[file.py:15-20]`

记住：**不知道的信息就调用工具查询，不要编造文件内容和代码细节。**"""


@dataclass
class ToolCall:
    tool: str
    parameters: Dict[str, Any]
    raw: str = ""


@dataclass
class AgentResponse:
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    iteration_count: int = 0


TOOL_FUNCTIONS: Dict[str, Callable] = {
    "read_file": lambda **p: read_file(p.get("file_path", ""), p.get("start_line"), p.get("end_line")),
    "list_directory": lambda **p: list_directory(p.get("dir_path", ""), p.get("show_hidden", False)),
    "get_file_info": lambda **p: get_file_info(p.get("file_path", "")),
    "extract_code_structure": lambda **p: extract_code_structure(p.get("code", ""), p.get("language", "Python")),
    "get_function_signatures": lambda **p: get_function_signatures(p.get("code", ""), p.get("language", "Python")),
}


class CodeExplainerAgent:
    def __init__(self):
        self.settings = get_settings()
        self.memory = ChatMemory(max_size=self.settings.max_memory_size)
        self.memory.set_system_prompt(SYSTEM_PROMPT_TEMPLATE)
        self.llm_client = None
        self._init_llm()

    def _init_llm(self) -> None:
        try:
            from langchain_openai import ChatOpenAI
            valid, msg = self.settings.validate()
            if not valid:
                print(f"[警告] {msg}，Agent 将使用 Mock 模式运行（不实际调用 LLM）。")
                return
            self.llm_client = ChatOpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                model=self.settings.openai_model,
                max_tokens=self.settings.max_tokens,
                temperature=self.settings.temperature,
            )
        except Exception as e:
            print(f"[警告] 初始化 LLM 客户端失败: {e}，Agent 将使用 Mock 模式运行。")
            self.llm_client = None

    def is_mock_mode(self) -> bool:
        return self.llm_client is None

    def _call_llm_with_retry(self, messages: List[Dict[str, str]]) -> str:
        if self.llm_client is None:
            return self._mock_llm_response(messages)
        last_error = None
        for attempt in range(1, self.settings.max_retry_attempts + 1):
            try:
                from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
                lc_messages = []
                for m in messages:
                    if m["role"] == "system":
                        lc_messages.append(SystemMessage(content=m["content"]))
                    elif m["role"] == "user":
                        lc_messages.append(HumanMessage(content=m["content"]))
                    else:
                        lc_messages.append(AIMessage(content=m["content"]))
                response = self.llm_client.invoke(lc_messages)
                return response.content if hasattr(response, "content") else str(response)
            except Exception as e:
                last_error = str(e)
                if attempt < self.settings.max_retry_attempts:
                    delay = self.settings.retry_delay_seconds * attempt
                    print(f"[重试 {attempt}/{self.settings.max_retry_attempts}] LLM 调用失败: {e}，{delay} 秒后重试...")
                    time.sleep(delay)
        raise RuntimeError(f"LLM 调用失败，已重试 {self.settings.max_retry_attempts} 次。最后错误: {last_error}")

    def _mock_llm_response(self, messages: List[Dict[str, str]]) -> str:
        last_user_msg = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user_msg = m["content"]
                break
        if "read_file" in last_user_msg or "读取" in last_user_msg or "read" in last_user_msg.lower():
            return (
                "好的，我来为您分析这段代码。\n\n"
                "**代码概述**: 这段代码实现了基本的数据处理功能。\n"
                "- 第1-5行: 导入必要的模块和定义常量\n"
                "- 第7-15行: `process_data()` 函数负责数据清洗和转换\n"
                "- 第17-25行: `main()` 函数作为程序入口\n\n"
                "**设计亮点**: 使用了函数式编程风格，每个函数职责单一。\n\n"
                "*(当前为 Mock 演示模式，如需真实 AI 分析，请在 .env 中配置 OPENAI_API_KEY)*"
            )
        return (
            "你好！我是 CodeExplainerAgent（代码解释助手）。\n\n"
            "我可以帮你：\n"
            "1. 📖 **解释代码逻辑** - 告诉我文件路径或贴出代码，我来逐段讲解\n"
            "2. ✏️ **生成代码注释** - 为你的代码生成规范的中文注释\n"
            "3. 🗂️ **分析代码结构** - 提取函数、类、依赖关系\n"
            "4. ❓ **回答代码问题** - 回答任何关于实现细节的疑问\n\n"
            "**使用示例**:\n"
            "- `请解释 examples/sample_code.py 的代码逻辑`\n"
            "- `分析一下这段冒泡排序的时间复杂度`\n"
            "- `为 main.py 生成详细注释`\n\n"
            "*(当前为 Mock 演示模式，如需真实 AI 分析，请在 .env 中配置 OPENAI_API_KEY)*"
        )

    def _parse_tool_calls(self, content: str) -> List[ToolCall]:
        calls: List[ToolCall] = []
        pattern = re.compile(r"```tool_call\s*(\{.*?\})\s*```", re.DOTALL)
        matches = pattern.findall(content)
        if not matches:
            pattern2 = re.compile(r"\{[\s\S]*?\"tool\"[\s\S]*?\"parameters\"[\s\S]*?\}")
            matches = pattern2.findall(content)
        for m in matches:
            try:
                data = json.loads(m)
                if "tool" in data and "parameters" in data:
                    calls.append(ToolCall(tool=data["tool"], parameters=data["parameters"], raw=m))
            except json.JSONDecodeError:
                continue
        return calls

    def _execute_tool(self, tool_call: ToolCall) -> Dict[str, Any]:
        result = {"tool": tool_call.tool, "parameters": tool_call.parameters, "success": False, "output": "", "error": ""}
        if tool_call.tool not in TOOL_FUNCTIONS:
            result["error"] = f"未知工具: {tool_call.tool}"
            return result
        try:
            func = TOOL_FUNCTIONS[tool_call.tool]
            raw_output = func(**tool_call.parameters)
            result["output"] = json.dumps(raw_output, ensure_ascii=False, indent=2)[:4000]
            result["success"] = raw_output.get("success", True) if isinstance(raw_output, dict) else True
            if isinstance(raw_output, dict) and raw_output.get("error"):
                result["error"] = raw_output["error"]
        except Exception as e:
            result["error"] = f"工具执行异常: {str(e)}"
        return result

    def run(self, user_input: str, max_iterations: int = 5) -> AgentResponse:
        response = AgentResponse(content="", iteration_count=0)
        if not user_input.strip():
            response.success = False
            response.error = "输入不能为空"
            return response
        self.memory.add_user_message(user_input)
        try:
            for iteration in range(max_iterations):
                response.iteration_count = iteration + 1
                messages = self.memory.get_messages_for_llm()
                llm_output = self._call_llm_with_retry(messages)
                tool_calls = self._parse_tool_calls(llm_output)
                if not tool_calls:
                    response.content = llm_output
                    self.memory.add_ai_message(llm_output)
                    return response
                response.tool_calls.extend(tool_calls)
                tool_responses_text = []
                for tc in tool_calls:
                    tool_result = self._execute_tool(tc)
                    response.tool_results.append(tool_result)
                    self.memory.add_tool_result(tc.tool, tool_result["output"][:500])
                    status = "成功" if tool_result["success"] else "失败"
                    tool_responses_text.append(
                        f"## 工具 {tc.tool} 调用结果 [{status}]\n"
                        f"参数: {json.dumps(tc.parameters, ensure_ascii=False)}\n"
                        f"输出:\n```json\n{tool_result['output']}\n```"
                        + (f"\n错误: {tool_result['error']}" if tool_result["error"] else "")
                    )
                combined = (
                    "以下是工具调用结果，请基于这些信息继续回答用户问题。"
                    "如果信息足够请直接回答，如果还需要其他信息请继续调用工具。\n\n"
                    + "\n\n".join(tool_responses_text)
                )
                self.memory.add_user_message(combined)
            response.content = "（Agent 已达到最大迭代次数，以下是最新回复：）\n" + llm_output
            return response
        except Exception as e:
            response.success = False
            response.error = f"Agent 运行时错误: {str(e)}"
            return response

    def clear_memory(self) -> None:
        self.memory.clear()
        self.memory.set_system_prompt(SYSTEM_PROMPT_TEMPLATE)

    def get_history(self) -> str:
        return self.memory.get_history_summary()
