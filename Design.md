# CodeExplainerAgent 设计文档

> 软件工程课程 Homework 1：Code Agent 设计说明

---

## 1. 设计目标

### 1.1 核心目标

构建一个符合 Agent 设计模式的**代码解释智能体**，掌握以下核心能力：

1. **LLM 调用能力**：通过主流框架接入大语言模型
2. **Prompt 设计**：设计专业的系统 Prompt 引导 Agent 正确使用工具并回答问题
3. **工具集成**：实现可被 Agent 调用的工具集（文件、代码分析等）
4. **Agent 循环**：实现「输入 → 推理 → 工具调用 → 再推理 → 输出」的 ReAct 式循环
5. **记忆机制**：维护对话历史，支持多轮上下文
6. **鲁棒性**：错误处理与自动重试机制

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **模块化** | 配置、Agent、工具、记忆、CLI 完全解耦，分层清晰 |
| **可扩展** | 新增工具只需注册到 `TOOL_FUNCTIONS` 字典，无需修改 Agent 核心 |
| **可运行** | 支持 Mock 模式，无 API Key 也能演示完整流程 |
| **可测试** | 每层均可独立单测，工具层无 LLM 依赖即可验证 |
| **用户友好** | CLI 提供大量便捷命令、状态输出、格式化打印 |

---

## 2. 总体架构

### 2.1 架构图（分层模式）

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI 交互层                            │
│  cli_app.py  -  命令解析、输出格式化、批量脚本、演示模式      │
└─────────────────────────────┬───────────────────────────────┘
                              │ 用户输入 / Agent 输出
┌─────────────────────────────▼───────────────────────────────┐
│                       Agent 核心层                           │
│  code_explainer_agent.py                                     │
│  ┌───────────┐  ┌─────────────┐  ┌───────────────────────┐  │
│  │ 系统Prompt │  │ LLM 调用器  │  │ ReAct 循环控制器      │  │
│  └───────────┘  └───┬─────────┘  │  · 工具调用解析       │  │
│                     │ 重试机制    │  · 多轮工具链执行     │  │
│                     ▼             └───────────┬───────────┘  │
└─────────────────────────────────────────────────┼────────────┘
                  工具调用                         │ 记忆读写
┌──────────────────┬──────────────────────────────┼────────────┐
│    工具层        │                     记忆层    │            │
│  (5 种工具)      │                   ChatMemory  │            │
│                  │                      │         │            │
│  read_file       │  ┌─────────────────▼────────┐ │            │
│  list_directory  │  │ 滑动窗口 deque(maxlen=N) │ │            │
│  get_file_info   │  │ System Prompt 独立管理   │ │            │
│  extract_...     │  │ 元数据附加存储           │ │            │
│  get_fn_sig      │  └──────────────────────────┘ │            │
└──────────────────┴───────────────────────────────┴────────────┘
                              ▲
┌─────────────────────────────┴───────────────────────────────┐
│                       配置层                                  │
│  Settings 单例  ←  python-dotenv  ←  .env 环境变量           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据流

```
用户输入问题
    │
    ▼
ChatMemory.add_user_message()
    │
    ▼
┌─ Agent.run() 循环 ─────────────────────────────────┐
│  迭代 i=1..max_iterations:                          │
│    1. 从 Memory 组装 messages                        │
│    2. _call_llm_with_retry(messages)  →  LLM 输出   │
│    3. _parse_tool_calls(output)                     │
│    4. 若无工具调用 → 记录到 Memory，返回响应        │
│    5. 若有工具调用:                                  │
│       → _execute_tool(tc) 调用对应工具函数           │
│       → 工具结果写回 Memory（作为用户消息）          │
│       → 进入下一次迭代（LLM 综合工具结果再推理）    │
└─────────────────────────────────────────────────────┘
    │
    ▼
格式化输出给用户
```

---

## 3. 模块详细设计

### 3.1 配置层 `config/settings.py`

**设计模式**：单例模式 (Singleton)

- `Settings.__new__` 保证全局唯一实例
- 启动时从 `.env` 加载所有配置（通过 `python-dotenv`）
- `validate()` 方法在 Agent 初始化时校验 API Key
- 关键配置项：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `openai_api_key` | - | API Key（必填，否则 Mock 模式） |
| `openai_base_url` | OpenAI 官方 | 兼容代理/其他厂商 |
| `openai_model` | `gpt-4o-mini` | 模型名称 |
| `max_tokens` | 2000 | 单次 LLM 调用最大输出 Token |
| `temperature` | 0.2 | 低温度保证答案稳定 |
| `max_memory_size` | 20 | 滑动窗口大小 |
| `max_retry_attempts` | 3 | LLM 调用失败重试次数 |
| `retry_delay_seconds` | 2.0 | 重试基础延迟（指数退避） |

### 3.2 工具层 `tools/`

**设计思想**：纯函数 + 统一返回格式

每个工具函数都返回 `dict`，统一包含 `success`、`error` 等字段，便于 Agent 判断调用结果。

#### 3.2.1 文件工具 `file_tools.py`

| 工具 | 功能 | 参数校验 | 错误处理 |
|------|------|----------|----------|
| `read_file` | 读取并带行号格式化代码 | 存在性/是否为文件/行号边界 | 编码错误、权限错误、行号越界 |
| `list_directory` | 列出目录内容（目录在前排序） | 存在性/是否为目录 | 权限错误 |
| `get_file_info` | 获取大小/行数/语言 | 存在性 | 通用异常捕获 |

支持识别 **28 种**编程语言文件后缀（`SUPPORTED_EXTENSIONS` 字典）。

#### 3.2.2 代码分析工具 `code_tools.py`

采用**正则+行扫描**实现多语言轻量 AST 提取：

| 语言 | 提取内容 |
|------|----------|
| Python | `import/from`、`class`、顶层/方法 `def`、`#注释`、`"""docstring"""` |
| JS/TS/Vue/JSX | `import`、`class`、`function`、箭头函数表达式 |
| Java/Kotlin/Scala | `import`、`class`、权限修饰的方法 |
| C/C++/C#/Go/Rust | `#include`、`class/struct`、函数声明 |
| 其他通用 | `func/function/def/fn` 关键字函数 |

输出统一结构：`{imports[], classes[ {name, methods[]} ], functions[], comments[]}`

### 3.3 记忆层 `memory/chat_memory.py`

**数据结构**：`collections.deque(maxlen=N)` 滑动窗口

- 超过 `max_size` 自动淘汰最旧消息
- System Prompt 独立存储，组装消息时自动放在首位
- 每条消息可附带 `metadata`（工具调用标记等）
- 提供 API：
  - `add_user_message / add_ai_message / add_tool_result`
  - `get_messages_for_llm()` → 直接喂给 LLM 的格式
  - `get_history_summary()` → 人类可读摘要
  - `clear()` → 清空记忆（不清除 System Prompt）

### 3.4 Agent 核心层 `agent/code_explainer_agent.py`

这是本项目最核心的模块。

#### 3.4.1 System Prompt 设计

`SYSTEM_PROMPT_TEMPLATE` 包含 5 部分关键引导：
1. **角色定义**：你是专业代码解释助手
2. **能力清单**：4 大核心能力（解释/注释/分析/问答）
3. **工具调用格式**：` ```tool_call {json} ``` ` 严格 Markdown 围栏
4. **工具文档**：5 个工具的名称、功能、参数表
5. **输出约束**：引用行号格式 `[file:15-20]`、不知道就调工具、禁止编造

#### 3.4.2 LLM 调用 + 重试

```python
def _call_llm_with_retry(messages):
    for attempt in 1..N:
        try: return ChatOpenAI.invoke(lc_messages)
        except:
            if last: raise
            sleep(delay * attempt)  # 线性退避
```

**Mock 模式降级方案**：当 LLM 不可用时，`_mock_llm_response()` 根据用户输入关键词给出有针对性的演示回复，保证 Agent 流程和工具调用链路 100% 可演示。

#### 3.4.3 工具调用解析

`_parse_tool_calls()` 采用**双重正则策略**保证鲁棒性：
1. 优先匹配严格的 ```tool_call ... ``` 围栏块
2. 若未命中，宽松匹配包含 `"tool"` 和 `"parameters"` 键的 JSON 对象
3. 解析失败忽略（当作纯文本回答）

#### 3.4.4 ReAct 多轮循环

`run(user_input, max_iterations=5)`：
- 最多 5 轮工具调用迭代，避免死循环
- 每轮流程：组装历史 → 调 LLM → 判工具 → 执行工具 → 写回工具结果 → 下一轮
- 工具结果以**用户消息**身份注入记忆，让 LLM 像读用户反馈一样消化工具输出

#### 3.4.5 工具注册机制

```python
TOOL_FUNCTIONS = {
    "read_file": lambda **p: read_file(p["file_path"], p.get("start_line"), p.get("end_line")),
    # ... 新增工具只需要加一行
}
```

**开闭原则**：新增工具无需修改 Agent 类，只需：
1. 在 `tools/` 下写函数
2. 加到 `tools/__init__.py` 导出
3. 在 `TOOL_FUNCTIONS` 注册
4. 在 System Prompt 中写文档

### 3.5 CLI 层 `cli/cli_app.py`

**三大运行模式**：

| 模式 | 触发方式 | 场景 |
|------|----------|------|
| 交互 REPL | `python main.py` | 日常对话，支持斜杠命令 |
| 单次查询 | `-q "问题" -f 文件` | 脚本调用、管道处理 |
| 批量脚本 | `--script file.txt` | 演示、回归测试 |
| 内置演示 | `--demo` | 无需输入快速展示全部能力 |

**斜杠命令机制**：输入以 `/` 开头直接走本地命令分支，无需调用 LLM，提高效率。

---

## 4. 错误处理与鲁棒性设计

| 层级 | 错误场景 | 处理策略 |
|------|----------|----------|
| **配置层** | API Key 缺失/占位符 | 降级 Mock 模式 + 显式警告 |
| **LLM 调用** | 网络异常、限流、超时 | 3 次重试 + 退避延迟 |
| **工具解析** | LLM 返回非 JSON、格式错误 | 容错忽略，当作纯文本回答 |
| **工具执行** | 文件不存在、无权限、行号越界 | 每个工具内部 try/catch，返回统一错误字段，Agent 将错误信息喂给 LLM 自己调整 |
| **Agent 循环** | 无限工具调用 | `max_iterations=5` 硬性终止 |
| **CLI 输入** | Ctrl+C / EOF | 优雅退出并打印再见 |

---

## 5. 测试策略

| 测试文件 | 覆盖范围 | 用例数 | 依赖 LLM |
|----------|----------|--------|----------|
| `tests/test_tools.py` | 文件读写、语言识别、代码结构提取（Python/JS）、签名提取 | 8 | ❌ 无 |
| `tests/test_agent.py` | 记忆容量、消息组装、工具解析正则、Mock 模式端到端、空输入防御 | 6 | ⚠️ 仅 Agent 集成用例走 Mock |

执行 `python -m unittest discover -s tests -v` 一键全量回归。

---

## 6. 评审标准映射

| 作业评审维度 | 本项目对应设计 |
|--------------|----------------|
| **功能完整性 40%** | 4 大功能（解释/注释/分析/问答）、5 个工具、CLI 全套命令、Mock 模式保证始终可用、边界情况全部 try/catch |
| **Agent 架构 30%** | 标准分层（Config/Tools/Memory/Agent/CLI）、ReAct 式推理循环、工具注册开闭原则、System Prompt 工程、滑动窗口记忆 |
| **代码质量 20%** | 单例模式、纯函数工具、统一返回格式、类型注解、dataclass 定义数据结构、完整单元测试、无循环依赖 |
| **文档 10%** | `README.md`（使用手册）+ `Design.md`（本设计文档，6 个章节覆盖架构/模块/错误/测试） |

---

## 7. 扩展方向（可选进阶）

1. **Web UI**：接入 Streamlit / Gradio 做网页版（CLI 层可轻松替换）
2. **更多工具**：Git 历史检索、代码执行沙箱、网络搜索、RAG 文档库
3. **多 Agent 协作**：引入 CrewAI / AutoGen，拆分为「读代码 Agent」「分析 Agent」「写注释 Agent」
4. **增量解析**：用 `tree-sitter` 替代正则做真正的多语言 AST
5. **流式输出**：改为 LLM streaming + SSE，优化打字机体验

---

## 8. 参考资料

- LangChain 官方文档：https://python.langchain.com/
- OpenAI API 文档：https://platform.openai.com/docs/
- ReAct 论文：*ReAct: Synergizing Reasoning and Acting in Language Models*
