import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.chat_memory import ChatMemory
from agent.code_explainer_agent import CodeExplainerAgent, ToolCall


class TestChatMemory(unittest.TestCase):
    def test_add_and_get_messages(self):
        mem = ChatMemory(max_size=5)
        mem.set_system_prompt("You are helpful")
        mem.add_user_message("Hello")
        mem.add_ai_message("Hi there")
        msgs = mem.get_messages_for_llm()
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[1]["role"], "user")
        self.assertEqual(msgs[2]["role"], "assistant")

    def test_size_limit(self):
        mem = ChatMemory(max_size=3)
        for i in range(10):
            mem.add_user_message(f"msg {i}")
        self.assertEqual(len(mem), 3)
        self.assertEqual(len(mem.messages), 3)

    def test_clear(self):
        mem = ChatMemory(max_size=10)
        mem.add_user_message("x")
        mem.clear()
        self.assertEqual(len(mem), 0)


class TestAgentParsing(unittest.TestCase):
    def test_parse_tool_call_fenced(self):
        content = """
Let me check the file first.
```tool_call
{"tool": "read_file", "parameters": {"file_path": "test.py"}}
```
"""
        from agent.code_explainer_agent import CodeExplainerAgent
        agent = CodeExplainerAgent()
        calls = agent._parse_tool_calls(content)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].tool, "read_file")
        self.assertEqual(calls[0].parameters["file_path"], "test.py")

    def test_parse_no_tool_call(self):
        from agent.code_explainer_agent import CodeExplainerAgent
        agent = CodeExplainerAgent()
        calls = agent._parse_tool_calls("这是普通回答，没有工具调用")
        self.assertEqual(len(calls), 0)


class TestAgentIntegration(unittest.TestCase):
    def test_agent_mock_mode_run(self):
        agent = CodeExplainerAgent()
        resp = agent.run("你好，请介绍一下你自己")
        self.assertIsNotNone(resp)
        self.assertTrue(len(resp.content) > 0)
        self.assertGreater(resp.iteration_count, 0)

    def test_agent_empty_input(self):
        agent = CodeExplainerAgent()
        resp = agent.run("   ")
        self.assertFalse(resp.success)
        self.assertIsNotNone(resp.error)


if __name__ == "__main__":
    unittest.main()
