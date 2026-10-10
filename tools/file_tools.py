import os
from typing import Optional


SUPPORTED_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".html": "HTML",
    ".css": "CSS",
    ".vue": "Vue",
    ".jsx": "React JSX",
    ".tsx": "React TSX",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".md": "Markdown",
    ".sh": "Shell",
    ".bat": "Batch",
    ".txt": "Text",
}


def read_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> dict:
    result = {"success": False, "content": "", "error": "", "language": "", "total_lines": 0, "lines": []}
    try:
        if not os.path.exists(file_path):
            result["error"] = f"文件不存在: {file_path}"
            return result
        if not os.path.isfile(file_path):
            result["error"] = f"路径不是文件: {file_path}"
            return result

        _, ext = os.path.splitext(file_path)
        result["language"] = SUPPORTED_EXTENSIONS.get(ext.lower(), "Unknown")

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        result["total_lines"] = len(all_lines)

        if start_line is not None or end_line is not None:
            s = max(1, start_line if start_line is not None else 1)
            e = min(len(all_lines), end_line if end_line is not None else len(all_lines))
            if s > len(all_lines):
                result["error"] = f"起始行号 {s} 超出文件总行数 {len(all_lines)}"
                return result
            selected_lines = all_lines[s - 1 : e]
            for i, line in enumerate(selected_lines, start=s):
                result["lines"].append({"line_num": i, "content": line.rstrip("\n")})
        else:
            for i, line in enumerate(all_lines, start=1):
                result["lines"].append({"line_num": i, "content": line.rstrip("\n")})

        formatted_lines = [f"{ln['line_num']:>4} | {ln['content']}" for ln in result["lines"]]
        result["content"] = "\n".join(formatted_lines)
        result["success"] = True
        return result
    except UnicodeDecodeError:
        result["error"] = f"文件编码无法读取，请确保是文本文件: {file_path}"
        return result
    except PermissionError:
        result["error"] = f"没有权限读取文件: {file_path}"
        return result
    except Exception as e:
        result["error"] = f"读取文件时出错: {str(e)}"
        return result


def list_directory(dir_path: str, show_hidden: bool = False) -> dict:
    result = {"success": False, "items": [], "error": "", "total": 0}
    try:
        if not os.path.exists(dir_path):
            result["error"] = f"目录不存在: {dir_path}"
            return result
        if not os.path.isdir(dir_path):
            result["error"] = f"路径不是目录: {dir_path}"
            return result

        entries = []
        with os.scandir(dir_path) as it:
            for entry in it:
                if not show_hidden and entry.name.startswith("."):
                    continue
                entry_type = "dir" if entry.is_dir() else "file"
                size = 0
                if entry.is_file():
                    try:
                        size = entry.stat().st_size
                    except OSError:
                        pass
                entries.append({"name": entry.name, "type": entry_type, "size": size})

        entries.sort(key=lambda x: (0 if x["type"] == "dir" else 1, x["name"].lower()))
        result["items"] = entries
        result["total"] = len(entries)
        result["success"] = True
        return result
    except PermissionError:
        result["error"] = f"没有权限访问目录: {dir_path}"
        return result
    except Exception as e:
        result["error"] = f"列出目录时出错: {str(e)}"
        return result


def get_file_info(file_path: str) -> dict:
    result = {"success": False, "info": {}, "error": ""}
    try:
        if not os.path.exists(file_path):
            result["error"] = f"文件不存在: {file_path}"
            return result

        stat = os.stat(file_path)
        _, ext = os.path.splitext(file_path)

        result["info"] = {
            "path": os.path.abspath(file_path),
            "name": os.path.basename(file_path),
            "extension": ext,
            "language": SUPPORTED_EXTENSIONS.get(ext.lower(), "Unknown"),
            "size_bytes": stat.st_size,
            "size_kb": round(stat.st_size / 1024, 2),
            "is_file": os.path.isfile(file_path),
            "is_dir": os.path.isdir(file_path),
        }
        if result["info"]["is_file"]:
            r = read_file(file_path)
            result["info"]["total_lines"] = r["total_lines"]
        result["success"] = True
        return result
    except Exception as e:
        result["error"] = f"获取文件信息时出错: {str(e)}"
        return result
