from __future__ import annotations
import heapq
import sys
from collections import deque, defaultdict
from typing import List, Tuple, Dict, Optional, Set


class TreeNode:
    def __init__(self, val: int = 0, left: Optional["TreeNode"] = None, right: Optional["TreeNode"] = None):
        self.val = val
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"TreeNode({self.val})"


class Graph:
    def __init__(self, n: int):
        self.n = n
        self.adj: Dict[int, List[Tuple[int, int]]] = defaultdict(list)

    def add_edge(self, u: int, v: int, w: int = 1) -> None:
        self.adj[u].append((v, w))
        self.adj[v].append((u, w))

    def dijkstra(self, start: int) -> List[int]:
        dist = [sys.maxsize] * self.n
        dist[start] = 0
        heap: List[Tuple[int, int]] = [(0, start)]
        visited: Set[int] = set()
        while heap:
            d, u = heapq.heappop(heap)
            if u in visited:
                continue
            visited.add(u)
            for v, w in self.adj[u]:
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    heapq.heappush(heap, (dist[v], v))
        return dist

    def bfs(self, start: int) -> List[int]:
        visited = [False] * self.n
        order: List[int] = []
        queue: deque[int] = deque([start])
        visited[start] = True
        while queue:
            u = queue.popleft()
            order.append(u)
            for v, _ in self.adj[u]:
                if not visited[v]:
                    visited[v] = True
                    queue.append(v)
        return order


class SegmentTree:
    def __init__(self, data: List[int]):
        self.n = len(data)
        self.size = 1
        while self.size < self.n:
            self.size *= 2
        self.tree = [0] * (2 * self.size)
        for i in range(self.n):
            self.tree[self.size + i] = data[i]
        for i in range(self.size - 1, 0, -1):
            self.tree[i] = self.tree[2 * i] + self.tree[2 * i + 1]

    def update(self, idx: int, value: int) -> None:
        idx += self.size
        self.tree[idx] = value
        idx //= 2
        while idx >= 1:
            self.tree[idx] = self.tree[2 * idx] + self.tree[2 * idx + 1]
            idx //= 2

    def query(self, l: int, r: int) -> int:
        res = 0
        l += self.size
        r += self.size
        while l <= r:
            if l % 2 == 1:
                res += self.tree[l]
                l += 1
            if r % 2 == 0:
                res += self.tree[r]
                r -= 1
            l //= 2
            r //= 2
        return res


def build_binary_tree(preorder: List[int], inorder: List[int]) -> Optional[TreeNode]:
    if not preorder or not inorder:
        return None
    root_val = preorder[0]
    root = TreeNode(root_val)
    mid = inorder.index(root_val)
    root.left = build_binary_tree(preorder[1 : mid + 1], inorder[:mid])
    root.right = build_binary_tree(preorder[mid + 1 :], inorder[mid + 1 :])
    return root


def inorder_traversal(root: Optional[TreeNode]) -> List[int]:
    result: List[int] = []
    stack: List[TreeNode] = []
    current = root
    while current or stack:
        while current:
            stack.append(current)
            current = current.left
        current = stack.pop()
        result.append(current.val)
        current = current.right
    return result


def longest_palindromic_substring(s: str) -> str:
    if not s:
        return ""
    n = len(s)
    start, max_len = 0, 1
    for i in range(n):
        l, r = i, i
        while l >= 0 and r < n and s[l] == s[r]:
            if r - l + 1 > max_len:
                max_len = r - l + 1
                start = l
            l -= 1
            r += 1
        l, r = i, i + 1
        while l >= 0 and r < n and s[l] == s[r]:
            if r - l + 1 > max_len:
                max_len = r - l + 1
                start = l
            l -= 1
            r += 1
    return s[start : start + max_len]


def lcs(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]


def main() -> None:
    print("=== 算法与数据结构测试代码 ===")

    preorder = [3, 9, 20, 15, 7]
    inorder = [9, 3, 15, 20, 7]
    tree_root = build_binary_tree(preorder, inorder)
    print("二叉树中序遍历:", inorder_traversal(tree_root))

    g = Graph(5)
    g.add_edge(0, 1, 4)
    g.add_edge(0, 2, 1)
    g.add_edge(2, 1, 2)
    g.add_edge(1, 3, 5)
    g.add_edge(2, 3, 8)
    g.add_edge(3, 4, 2)
    print("Dijkstra 从 0 出发最短距离:", g.dijkstra(0))
    print("BFS 从 0 出发遍历顺序:", g.bfs(0))

    seg = SegmentTree([1, 3, 5, 7, 9, 11])
    print("线段树 [1,4] 区间和:", seg.query(1, 4))
    seg.update(3, 0)
    print("更新索引3为0后 [1,4] 区间和:", seg.query(1, 4))

    s = "abracadabra"
    print(f"'{s}' 的最长回文子串: '{longest_palindromic_substring(s)}'")
    print(f"LCS('abcde','ace') =", lcs("abcde", "ace"))


if __name__ == "__main__":
    main()
