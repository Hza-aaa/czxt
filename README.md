# CodeExplainerAgent - 代码解释助手

> 软件工程课程 Homework 1：Code Agent 项目

## 项目简介

CodeExplainerAgent 是一个基于 LLM + LangChain 的代码解释智能体（Agent）。它可以帮助开发者理解代码逻辑、生成中文注释、分析代码结构并回答各类代码相关问题。

本项目完整实现了 Agent 的基础架构：**输入 → 推理 → 工具调用 → 输出** 的核心循环，并支持上下文记忆、错误重试和多工具协同。

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 📖 **代码解释** | 逐行/逐段解释代码功能、算法原理、设计意图，引用精确行号 |
| ✏️ **注释生成** | 为代码生成规范、清晰的中文注释 |
| 🗂️ **结构分析** | 自动提取函数、类、方法、导入项、注释等代码结构信息 |
| 🔍 **问题回答** | 回答实现细节、复杂度分析、调用关系、依赖关系等问题 |
| 🛠️ **工具集成** | 内置 5 种工具：文件读取、目录浏览、文件信息、结构分析、签名提取 |
| 🧠 **上下文记忆** | 自动维护对话历史，支持多轮追问 |
| ♻️ **错误重试** | LLM 调用失败自动指数退避重试（默认 3 次） |
| 💻 **CLI 交互** | 丰富的命令行界面，支持脚本批处理、单次查询、交互对话 |
| 🧪 **单元测试** | 完整的单元测试套件，覆盖工具层、记忆层、Agent 层 |

---

## 📁 项目结构

```
第一次作业/
├── main.py                     # 程序入口
├── requirements.txt            # 依赖清单
├── .env / .env.example         # 环境变量配置（LLM API Key）
│
├── config/                     # 配置模块
│   ├── __init__.py
│   └── settings.py             # 单例配置管理 + 环境变量加载
│
├── agent/                      # Agent 核心模块
│   ├── __init__.py
│   └── code_explainer_agent.py # Agent 主循环、Prompt、工具调用解析、重试机制
│
├── tools/                      # 工具层（5 个工具）
│   ├── __init__.py
│   ├── file_tools.py           # read_file / list_directory / get_file_info
│   └── code_tools.py           # extract_code_structure / get_function_signatures
│
├── memory/                     # 记忆模块
│   ├── __init__.py
│   └── chat_memory.py          # 对话记忆（滑动窗口 + System Prompt 管理）
│
├── cli/                        # 交互界面
│   ├── __init__.py
│   └── cli_app.py              # CLI 命令解析、格式化输出、批量脚本
│
├── examples/                   # 示例和演示
│   ├── sample_code.py          # 综合示例代码（排序、搜索、类设计）
│   └── demo_script.txt         # 演示用命令脚本
│
└── tests/                      # 单元测试
    ├── __init__.py
    ├── test_tools.py           # 工具层测试（8 个用例）
    └── test_agent.py           # Agent / 记忆层测试（6 个用例）
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

或单独安装：

```bash
pip install langchain langchain-openai langchain-core python-dotenv
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 API 信息：

```ini
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
MAX_TOKENS=2000
TEMPERATURE=0.2
```

> 💡 **支持所有 OpenAI 兼容 API**（如 DashScope、DeepSeek、硅基流动、本地 Ollama 等），只需修改 `OPENAI_BASE_URL` 即可。
>
> 💡 如果**暂不配置 API Key**，Agent 会自动进入 **Mock 演示模式**，不调用真实 LLM 也能演示完整 Agent 流程和工具调用。

### 3. 运行演示

```bash
# 方式一：交互模式（推荐）
python main.py

# 方式二：一键运行内置演示用例
python main.py --demo

# 方式三：从脚本批量运行
python main.py --script examples/demo_script.txt

# 方式四：单次查询后退出
python main.py -q "请解释 examples/sample_code.py 中 quick_sort 的原理"
```

---

## ⌨️ 交互命令

进入交互模式后（`python main.py`），除了直接输入问题外，还支持以下**斜杠命令**：

| 命令 | 缩写 | 说明 |
|------|------|------|
| `/help` | `/?` | 显示帮助 |
| `/clear` | `/c` | 清空对话记忆 |
| `/history` | `/h` | 查看最近对话历史 |
| `/status` | `/s` | 查看 Agent 状态和配置 |
| `/tools` | `/t` | 列出所有可用工具 |
| `/read <path> [s] [e]` | - | 手动读取文件（支持按行号范围） |
| `/explain <path>` | - | 快速解释整个文件 |
| `/struct <path>` | - | 分析并打印代码结构 |
| `/save <file.json>` | - | 保存对话到 JSON 文件 |
| `/quit` | `/q` | 退出程序 |

**交互示例：**
```
你> /struct examples/sample_code.py
你> 请解释 quick_sort 函数的时间复杂度和实现细节
你> 为 DataProcessor 类的 process 方法生成详细注释
```

---

## 🧪 运行测试

```bash
# 运行所有测试
python -m unittest discover -s tests -v

# 单独运行工具层测试
python -m unittest tests.test_tools -v

# 单独运行 Agent 层测试
python -m unittest tests.test_agent -v
```

预期结果：`tests.test_tools` 的 8 个测试用例全部通过；`tests.test_agent` 在依赖齐全时 6 个用例全部通过。

---

## 📋 技术栈

| 类别 | 选型 |
|------|------|
| **编程语言** | Python 3.10+ |
| **Agent 框架** | LangChain / LangChain Core |
| **LLM 接入** | LangChain OpenAI（兼容所有 OpenAI 格式 API） |
| **配置管理** | python-dotenv + 单例模式 Settings |
| **交互界面** | 原生 CLI（argparse 命令行解析） |
| **测试框架** | unittest（标准库） |

---

## 📦 提交物清单

- ✅ **提交物 1 / 代码**：本项目完整源代码
- ✅ **提交物 2 / 文档**：`README.md`（本文件）+ `Design.md`（设计文档）
- ⏳ **提交物 3 / 演示视频**：可选（用户自行录制 1 分钟以内）
- 📦 **打包**：所有内容打包为 "学号姓名.rar/zip" 提交

---

## 📄 License

本项目为软件工程课程作业，仅用于学习与教学用途。
