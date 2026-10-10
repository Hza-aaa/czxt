from typing import List, Dict, Optional
from collections import deque


class ChatMemory:
    def __init__(self, max_size: int = 20):
        self.max_size = max_size
        self.messages: deque = deque(maxlen=max_size)
        self.system_prompt: Optional[str] = None

    def set_system_prompt(self, prompt: str) -> None:
        self.system_prompt = prompt

    def add_user_message(self, content: str, metadata: Optional[Dict] = None) -> None:
        msg = {"role": "user", "content": content}
        if metadata:
            msg["metadata"] = metadata
        self.messages.append(msg)

    def add_ai_message(self, content: str, metadata: Optional[Dict] = None) -> None:
        msg = {"role": "assistant", "content": content}
        if metadata:
            msg["metadata"] = metadata
        self.messages.append(msg)

    def add_tool_result(self, tool_name: str, result_summary: str) -> None:
        msg = {
            "role": "assistant",
            "content": f"[工具调用: {tool_name}]\n结果摘要: {result_summary}",
            "metadata": {"type": "tool_result", "tool": tool_name},
        }
        self.messages.append(msg)

    def get_messages_for_llm(self, include_system: bool = True) -> List[Dict[str, str]]:
        result: List[Dict[str, str]] = []
        if include_system and self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})
        for msg in self.messages:
            result.append({"role": msg["role"], "content": msg["content"]})
        return result

    def get_history_summary(self) -> str:
        if not self.messages:
            return "暂无历史对话"
        lines = []
        for msg in list(self.messages)[-10:]:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"]
            if len(content) > 100:
                content = content[:100] + "..."
            lines.append(f"[{role}]: {content}")
        return "\n".join(lines)

    def clear(self) -> None:
        self.messages.clear()

    def __len__(self) -> int:
        return len(self.messages)

    def __repr__(self) -> str:
        return f"ChatMemory(max_size={self.max_size}, current={len(self.messages)})"
