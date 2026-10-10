import sys
import os
import io
import json
import argparse
from typing import Optional

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from agent import CodeExplainerAgent, AgentResponse
from config import get_settings


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║            CodeExplainerAgent - 代码解释助手                 ║
║                    软件工程作业 Homework 1                    ║
╚══════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
可用命令:
  /help, /?           - 显示此帮助信息
  /clear, /c          - 清空对话历史记忆
  /history, /h        - 查看最近对话历史
  /status, /s         - 显示 Agent 状态和配置
  /tools, /t          - 列出所有可用工具
  /read <path> [start] [end]  - 手动读取文件（示例: /read examples/sample_code.py）
  /explain <path>     - 快速解释整个文件（示例: /explain main.py）
  /struct <path>      - 分析文件代码结构（示例: /struct main.py）
  /save <file>        - 将当前对话保存到 JSON 文件
  /quit, /exit, /q    - 退出程序

直接输入问题即可与 Agent 对话，例如:
  > 请解释 examples/sample_code.py 中 quick_sort 函数的逻辑
  > 帮我为 main.py 生成详细的中文注释
"""


def print_banner() -> None:
    print(BANNER)


def _format_response(resp: AgentResponse) -> str:
    output_parts = []
    if resp.tool_calls:
        output_parts.append("\n🔧 **调用了以下工具:**")
        for i, tc in enumerate(resp.tool_calls, 1):
            output_parts.append(f"  {i}. `{tc.tool}` 参数: {json.dumps(tc.parameters, ensure_ascii=False)}")
    if resp.tool_results:
        output_parts.append("\n📊 **工具执行结果:**")
        for r in resp.tool_results:
            if r["success"]:
                output_parts.append(f"  ✅ {r['tool']}: 执行成功")
            else:
                output_parts.append(f"  ❌ {r['tool']}: 失败 - {r['error']}")
    output_parts.append(f"\n🤖 迭代次数: {resp.iteration_count}")
    output_parts.append("\n" + "=" * 60 + "\n")
    output_parts.append(resp.content if resp.success else f"[错误] {resp.error}")
    return "\n".join(output_parts)


def _cmd_read(agent: CodeExplainerAgent, args: list[str]) -> None:
    if not args:
        print("用法: /read <文件路径> [起始行] [结束行]")
        return
    from tools import read_file
    path = args[0]
    s = int(args[1]) if len(args) > 1 else None
    e = int(args[2]) if len(args) > 2 else None
    result = read_file(path, s, e)
    if not result["success"]:
        print(f"❌ 读取失败: {result['error']}")
        return
    print(f"📄 文件: {path} (语言: {result['language']}, 共 {result['total_lines']} 行)")
    print("-" * 60)
    print(result["content"])


def _cmd_struct(agent: CodeExplainerAgent, args: list[str]) -> None:
    if not args:
        print("用法: /struct <文件路径>")
        return
    from tools import read_file, extract_code_structure
    path = args[0]
    r = read_file(path)
    if not r["success"]:
        print(f"❌ 读取失败: {r['error']}")
        return
    raw_code = "\n".join(ln["content"] for ln in r["lines"])
    struct = extract_code_structure(raw_code, r["language"])
    print(f"📐 代码结构分析 - {path} ({r['language']})")
    print("-" * 60)
    if struct.get("imports"):
        print(f"\n📦 导入项 ({len(struct['imports'])}):")
        for imp in struct["imports"]:
            print(f"  [L{imp['line']}] {imp['content']}")
    if struct.get("classes"):
        print(f"\n🏷️  类 ({len(struct['classes'])}):")
        for cls in struct["classes"]:
            print(f"  [L{cls['line']}] class {cls['name']}")
            for m in cls.get("methods", []):
                print(f"         └─ [L{m['line']}] {m['name']}({m.get('parameters','')})")
    if struct.get("functions"):
        print(f"\n🔧 函数 ({len(struct['functions'])}):")
        for fn in struct["functions"]:
            rt = f" -> {fn['return_type']}" if fn.get("return_type") else ""
            print(f"  [L{fn['line']}] {fn['name']}({fn.get('parameters','')}){rt}")
    if struct.get("comments"):
        print(f"\n💬 注释 ({len(struct['comments'])} 处, 显示前5条):")
        for cm in struct["comments"][:5]:
            txt = cm["content"]
            if len(txt) > 80:
                txt = txt[:80] + "..."
            print(f"  [L{cm['line']}] {txt}")


def _cmd_status(agent: CodeExplainerAgent) -> None:
    settings = get_settings()
    ok, msg = settings.validate()
    mode = "Mock 模式" if agent.is_mock_mode() else "真实 LLM 模式"
    print(f"""
📋 Agent 状态:
  模式:       {mode}
  模型:       {settings.openai_model}
  API Key:    {'已配置' if ok else '未配置'} ({msg})
  对话记录:   {len(agent.memory)} 条
  最大记忆:   {settings.max_memory_size} 条
  最大重试:   {settings.max_retry_attempts} 次
""")


def _cmd_tools() -> None:
    print("""
🛠️  可用工具列表:
  1. read_file                 - 读取文件内容（支持按行号范围）
  2. list_directory            - 列出目录内容
  3. get_file_info             - 获取文件大小/行数/语言等信息
  4. extract_code_structure    - 提取代码结构（函数/类/导入/注释）
  5. get_function_signatures   - 提取所有函数签名
""")


def _cmd_save(agent: CodeExplainerAgent, args: list[str]) -> None:
    if not args:
        print("用法: /save <文件名.json>")
        return
    data = {
        "system_prompt": agent.memory.system_prompt,
        "messages": list(agent.memory.messages),
    }
    try:
        with open(args[0], "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 对话已保存到 {args[0]}")
    except Exception as e:
        print(f"❌ 保存失败: {e}")


def run_interactive(script: Optional[list[str]] = None) -> int:
    print_banner()
    agent = CodeExplainerAgent()
    settings = get_settings()
    valid, _ = settings.validate()
    if not valid:
        print("⚠️  提示: 未检测到有效的 API Key，当前运行在 Mock 演示模式。")
        print("   编辑 .env 文件配置 OPENAI_API_KEY 后即可启用真实 AI 能力。\n")
    print("输入 /help 查看所有命令，输入问题开始对话，输入 /quit 退出。\n")

    if script:
        for line in script:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            print(f">>> {line}")
            _handle_input(agent, line)
        print("\n✅ 脚本执行完毕")
        return 0

    while True:
        try:
            user_input = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n再见！")
            return 0
        if not user_input:
            continue
        if user_input.lower() in ("/quit", "/exit", "/q"):
            print("再见！")
            return 0
        _handle_input(agent, user_input)


def _handle_input(agent: CodeExplainerAgent, user_input: str) -> None:
    if user_input.startswith("/"):
        _handle_command(agent, user_input)
        return
    print("\n⏳ 思考中...", end="", flush=True)
    resp = agent.run(user_input)
    print("\r" + " " * 40 + "\r")
    print(_format_response(resp))


def _handle_command(agent: CodeExplainerAgent, cmd: str) -> None:
    parts = cmd.split()
    name = parts[0].lower()
    args = parts[1:]
    if name in ("/help", "/?"):
        print(HELP_TEXT)
    elif name in ("/clear", "/c"):
        agent.clear_memory()
        print("✅ 对话记忆已清空")
    elif name in ("/history", "/h"):
        print("📜 最近对话历史:")
        print("-" * 60)
        print(agent.get_history())
    elif name in ("/status", "/s"):
        _cmd_status(agent)
    elif name in ("/tools", "/t"):
        _cmd_tools()
    elif name == "/read":
        _cmd_read(agent, args)
    elif name in ("/explain", "/struct"):
        if not args:
            print(f"用法: {name} <文件路径>")
            return
        if name == "/struct":
            _cmd_struct(agent, args)
        else:
            question = f"请详细解释 {args[0]} 这个文件的代码逻辑，包括整体结构、关键函数和设计意图。"
            print(f"⏳ 正在分析 {args[0]} ...")
            resp = agent.run(question)
            print(_format_response(resp))
    elif name == "/save":
        _cmd_save(agent, args)
    else:
        print(f"未知命令: {name}。输入 /help 查看可用命令。")


def run_once(query: str, file_path: Optional[str] = None) -> int:
    agent = CodeExplainerAgent()
    if file_path:
        user_input = f"文件 {file_path} 的情况：{query}"
    else:
        user_input = query
    resp = agent.run(user_input)
    print(_format_response(resp))
    return 0 if resp.success else 1


def run_cli() -> int:
    parser = argparse.ArgumentParser(
        prog="CodeExplainerAgent",
        description="代码解释助手 Agent - 解释代码逻辑、生成注释、回答代码问题",
    )
    parser.add_argument("-q", "--query", type=str, help="一次性查询，执行后立即退出")
    parser.add_argument("-f", "--file", type=str, help="配合 -q 使用，指定要分析的文件路径")
    parser.add_argument("--script", type=str, help="从文本文件批量执行命令/问题（每行一条）")
    parser.add_argument("--demo", action="store_true", help="运行内置演示用例")
    args = parser.parse_args()

    if args.demo:
        demo_lines = [
            "/status",
            "/tools",
            "你好，介绍一下你自己",
            "/struct examples/sample_code.py",
            "请解释 examples/sample_code.py 中 quick_sort 函数的实现原理和时间复杂度",
            "/history",
        ]
        return run_interactive(demo_lines)
    if args.script:
        if not os.path.exists(args.script):
            print(f"脚本文件不存在: {args.script}")
            return 1
        with open(args.script, "r", encoding="utf-8") as f:
            lines = [ln.rstrip("\n") for ln in f if ln.strip()]
        return run_interactive(lines)
    if args.query:
        return run_once(args.query, args.file)
    return run_interactive()
