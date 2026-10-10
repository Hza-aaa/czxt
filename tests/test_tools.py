import sys
import os
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.file_tools import read_file, list_directory, get_file_info
from tools.code_tools import extract_code_structure, get_function_signatures


class TestFileTools(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.py")
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("# Line 1: comment\n")
            f.write("def hello(name):\n")
            f.write("    print(f'Hello, {name}')\n")
            f.write("    return True\n")
            f.write("\n")
            f.write("class Greeter:\n")
            f.write("    def __init__(self, greeting='Hi'):\n")
            f.write("        self.greeting = greeting\n")

    def test_read_file_success(self):
        result = read_file(self.test_file)
        self.assertTrue(result["success"])
        self.assertEqual(result["total_lines"], 8)
        self.assertEqual(result["language"], "Python")
        self.assertEqual(len(result["lines"]), 8)
        self.assertEqual(result["lines"][0]["line_num"], 1)
        self.assertIn("Line 1", result["lines"][0]["content"])

    def test_read_file_range(self):
        result = read_file(self.test_file, start_line=2, end_line=4)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["lines"]), 3)
        self.assertEqual(result["lines"][0]["line_num"], 2)
        self.assertEqual(result["lines"][-1]["line_num"], 4)

    def test_read_file_not_found(self):
        result = read_file("/path/does/not/exist.py")
        self.assertFalse(result["success"])
        self.assertIn("不存在", result["error"])

    def test_list_directory(self):
        result = list_directory(self.temp_dir)
        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["name"], "test.py")
        self.assertEqual(result["items"][0]["type"], "file")

    def test_get_file_info(self):
        result = get_file_info(self.test_file)
        self.assertTrue(result["success"])
        self.assertEqual(result["info"]["name"], "test.py")
        self.assertEqual(result["info"]["language"], "Python")
        self.assertTrue(result["info"]["is_file"])
        self.assertIn("total_lines", result["info"])


class TestCodeTools(unittest.TestCase):
    def test_extract_python_structure(self):
        code = """
import os
from typing import List

CONST = 42

def add(a: int, b: int) -> int:
    return a + b

class Calculator:
    def __init__(self, value=0):
        self.value = value

    def multiply(self, x: int) -> int:
        return self.value * x
"""
        struct = extract_code_structure(code, "Python")
        self.assertTrue(struct["success"])
        self.assertGreaterEqual(len(struct["imports"]), 2)
        self.assertEqual(len(struct["classes"]), 1)
        self.assertEqual(struct["classes"][0]["name"], "Calculator")
        self.assertGreaterEqual(len(struct["classes"][0]["methods"]), 2)
        self.assertEqual(len(struct["functions"]), 1)
        self.assertEqual(struct["functions"][0]["name"], "add")

    def test_extract_js_structure(self):
        code = """
import React from 'react';
import { useState } from 'react';

function App(props) {
    const [count, setCount] = useState(0);
    return <div>{count}</div>;
}

const handleClick = (e) => {
    console.log(e);
};

class MyClass {
    constructor() { this.x = 1; }
    doSomething() { return this.x; }
}
"""
        struct = extract_code_structure(code, "JavaScript")
        self.assertTrue(struct["success"])
        self.assertGreaterEqual(len(struct["imports"]), 2)
        self.assertEqual(len(struct["classes"]), 1)
        self.assertGreaterEqual(len(struct["functions"]), 2)

    def test_get_function_signatures(self):
        code = """
def foo(a, b: int = 5) -> str:
    return str(a + b)

class Bar:
    def baz(self, x):
        return x * 2
"""
        sigs = get_function_signatures(code, "Python")
        self.assertTrue(sigs["success"])
        self.assertGreaterEqual(sigs["total"], 2)
        sig_names = [s["signature"] for s in sigs["signatures"]]
        self.assertTrue(any("foo(a, b: int = 5) -> str" in s for s in sig_names))
        self.assertTrue(any("Bar.baz" in s for s in sig_names))


if __name__ == "__main__":
    unittest.main()
