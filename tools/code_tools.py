import re
from typing import Optional


def extract_code_structure(code: str, language: str = "Python") -> dict:
    result = {"success": True, "functions": [], "classes": [], "imports": [], "comments": []}
    try:
        lines = code.split("\n")
        if language.lower() in ["python", "py"]:
            result = _extract_python_structure(lines, result)
        elif language.lower() in ["javascript", "js", "typescript", "ts", "vue", "jsx", "tsx"]:
            result = _extract_js_structure(lines, result)
        elif language.lower() in ["java", "kotlin", "kt", "scala"]:
            result = _extract_java_structure(lines, result)
        elif language.lower() in ["c", "c++", "cpp", "cs", "c#", "go", "rust", "rs"]:
            result = _extract_c_style_structure(lines, result)
        else:
            result = _extract_generic_structure(lines, result)
        return result
    except Exception as e:
        result["success"] = False
        result["error"] = f"解析代码结构时出错: {str(e)}"
        return result


def _extract_python_structure(lines: list[str], result: dict) -> dict:
    import_pattern = re.compile(r"^\s*(import|from)\s+(.+)")
    class_pattern = re.compile(r"^class\s+(\w+)(\(.*?\))?\s*:")
    func_pattern = re.compile(r"^(\s*)def\s+(\w+)\s*\((.*?)\)\s*(->\s*.*?)?\s*:")
    comment_pattern = re.compile(r"^\s*#(.+)")
    docstring_pattern = re.compile(r'^\s*"""(.+?)"""')
    docstring_pattern2 = re.compile(r"^\s*'''(.+?)'''")

    current_class = None
    for i, line in enumerate(lines, start=1):
        imp = import_pattern.match(line)
        if imp:
            result["imports"].append({"line": i, "content": imp.group(2).strip()})
            continue
        cls = class_pattern.match(line)
        if cls:
            current_class = cls.group(1)
            result["classes"].append({"line": i, "name": current_class, "methods": []})
            continue
        fn = func_pattern.match(line)
        if fn:
            indent = len(fn.group(1))
            name = fn.group(2)
            params = fn.group(3).strip()
            return_type = fn.group(4).strip().lstrip("->").strip() if fn.group(4) else ""
            entry = {
                "line": i,
                "name": name,
                "parameters": params,
                "return_type": return_type,
            }
            if indent > 0 and current_class:
                for c in result["classes"]:
                    if c["name"] == current_class:
                        c["methods"].append(entry)
                        break
            else:
                current_class = None
                result["functions"].append(entry)
            continue
        cm = comment_pattern.match(line)
        if cm:
            result["comments"].append({"line": i, "content": cm.group(1).strip()})
            continue
        ds = docstring_pattern.match(line) or docstring_pattern2.match(line)
        if ds:
            result["comments"].append({"line": i, "content": "[docstring] " + ds.group(1).strip()})
    return result


def _extract_js_structure(lines: list[str], result: dict) -> dict:
    import_pattern = re.compile(r"^\s*(import|const|let|var)\s+(?:.+?from\s+)?['\"](.+?)['\"]")
    class_pattern = re.compile(r"^\s*class\s+(\w+)")
    func_patterns = [
        re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\((.*?)\)"),
        re.compile(r"^\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\((.*?)\)\s*=>"),
        re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(\w+)\s*\((.*?)\)\s*\{"),
    ]
    for i, line in enumerate(lines, start=1):
        imp = import_pattern.match(line)
        if imp:
            result["imports"].append({"line": i, "content": imp.group(2).strip()})
            continue
        cls = class_pattern.match(line)
        if cls:
            result["classes"].append({"line": i, "name": cls.group(1), "methods": []})
            continue
        for fp in func_patterns:
            fn = fp.match(line)
            if fn:
                result["functions"].append({
                    "line": i,
                    "name": fn.group(1),
                    "parameters": fn.group(2).strip(),
                })
                break
    return result


def _extract_java_structure(lines: list[str], result: dict) -> dict:
    import_pattern = re.compile(r"^\s*import\s+(.+?);")
    class_pattern = re.compile(r"^\s*(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)")
    func_pattern = re.compile(
        r"^\s*(?:public|private|protected)?\s*(?:static|final|abstract)?\s*[\w<>\[\]]+\s+(\w+)\s*\((.*?)\)"
    )
    for i, line in enumerate(lines, start=1):
        imp = import_pattern.match(line)
        if imp:
            result["imports"].append({"line": i, "content": imp.group(1).strip()})
            continue
        cls = class_pattern.match(line)
        if cls:
            result["classes"].append({"line": i, "name": cls.group(1), "methods": []})
            continue
        fn = func_pattern.match(line)
        if fn and fn.group(1) not in ("class", "if", "for", "while", "switch"):
            params = fn.group(2).strip()
            result["functions"].append({"line": i, "name": fn.group(1), "parameters": params})
    return result


def _extract_c_style_structure(lines: list[str], result: dict) -> dict:
    include_pattern = re.compile(r'^\s*#\s*include\s*[<"](.+?)[>"]')
    func_pattern = re.compile(r"^\s*[\w:*]+\s+(\w+)\s*\((.*?)\)\s*(?:const)?\s*\{?")
    class_pattern = re.compile(r"^\s*(?:class|struct|interface)\s+(\w+)")
    for i, line in enumerate(lines, start=1):
        inc = include_pattern.match(line)
        if inc:
            result["imports"].append({"line": i, "content": inc.group(1).strip()})
            continue
        cls = class_pattern.match(line)
        if cls:
            result["classes"].append({"line": i, "name": cls.group(1), "methods": []})
            continue
        fn = func_pattern.match(line)
        skip_keywords = {"if", "for", "while", "switch", "catch", "return", "sizeof", "typeof", "alignof"}
        if fn and fn.group(1) not in skip_keywords and not fn.group(1).startswith("#"):
            params = fn.group(2).strip()
            result["functions"].append({"line": i, "name": fn.group(1), "parameters": params})
    return result


def _extract_generic_structure(lines: list[str], result: dict) -> dict:
    func_pattern = re.compile(r"^\s*(?:func|function|def|fn|proc|sub)\s+(\w+)")
    for i, line in enumerate(lines, start=1):
        fn = func_pattern.match(line)
        if fn:
            result["functions"].append({"line": i, "name": fn.group(1), "parameters": ""})
    return result


def get_function_signatures(code: str, language: str = "Python") -> dict:
    structure = extract_code_structure(code, language)
    signatures = []
    for fn in structure.get("functions", []):
        sig = f"{fn['name']}({fn.get('parameters', '')})"
        if fn.get("return_type"):
            sig += f" -> {fn['return_type']}"
        signatures.append({"line": fn["line"], "signature": sig})
    for cls in structure.get("classes", []):
        for m in cls.get("methods", []):
            sig = f"{cls['name']}.{m['name']}({m.get('parameters', '')})"
            if m.get("return_type"):
                sig += f" -> {m['return_type']}"
            signatures.append({"line": m["line"], "signature": sig})
    return {"success": True, "signatures": signatures, "total": len(signatures)}
