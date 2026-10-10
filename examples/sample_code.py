import random
import time
from typing import List, Optional, Tuple


DATA_CACHE = {}
MAX_CACHE_SIZE = 1000


def generate_random_list(size: int, min_val: int = 0, max_val: int = 100) -> List[int]:
    if size <= 0:
        return []
    if size > 100000:
        size = 100000
    return [random.randint(min_val, max_val) for _ in range(size)]


def quick_sort(arr: List[int], low: Optional[int] = None, high: Optional[int] = None) -> List[int]:
    if low is None:
        low = 0
    if high is None:
        high = len(arr) - 1
    if low < high:
        pivot_index = _partition(arr, low, high)
        quick_sort(arr, low, pivot_index - 1)
        quick_sort(arr, pivot_index + 1, high)
    return arr


def _partition(arr: List[int], low: int, high: int) -> int:
    pivot = arr[high]
    i = low - 1
    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1


def binary_search(arr: List[int], target: int) -> int:
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1


def cached(func):
    def wrapper(*args):
        key = (func.__name__, args)
        if key in DATA_CACHE:
            return DATA_CACHE[key]
        result = func(*args)
        if len(DATA_CACHE) < MAX_CACHE_SIZE:
            DATA_CACHE[key] = result
        return result
    return wrapper


@cached
def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


class DataProcessor:
    def __init__(self, name: str = "DefaultProcessor"):
        self.name = name
        self.processed_count = 0
        self.history: List[Tuple[int, float]] = []

    def process(self, data: List[int]) -> Tuple[float, float, float]:
        if not data:
            raise ValueError("Empty data list")
        start = time.time()
        sorted_data = quick_sort(data.copy())
        total = sum(sorted_data)
        n = len(sorted_data)
        mean_val = total / n
        if n % 2 == 0:
            median_val = (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
        else:
            median_val = sorted_data[n // 2]
        variance = sum((x - mean_val) ** 2 for x in sorted_data) / n
        std_val = variance ** 0.5
        elapsed = time.time() - start
        self.processed_count += 1
        self.history.append((n, elapsed))
        return mean_val, median_val, std_val

    def get_stats(self) -> dict:
        total_items = sum(h[0] for h in self.history)
        total_time = sum(h[1] for h in self.history)
        avg_time = total_time / self.processed_count if self.processed_count > 0 else 0
        return {
            "processor_name": self.name,
            "processed_count": self.processed_count,
            "total_items_processed": total_items,
            "total_processing_time": round(total_time, 6),
            "average_time_per_batch": round(avg_time, 6),
        }


def main() -> None:
    print("=== Data Processor Demo ===")
    processor = DataProcessor("MyProcessor")
    raw_data = generate_random_list(20, 1, 50)
    print(f"原始数据: {raw_data}")
    mean, median, std = processor.process(raw_data)
    print(f"均值: {mean:.2f}, 中位数: {median:.2f}, 标准差: {std:.2f}")
    sorted_arr = quick_sort(raw_data.copy())
    target = sorted_arr[len(sorted_arr) // 2]
    idx = binary_search(sorted_arr, target)
    print(f"二分查找 {target}: 位置 {idx}")
    print(f"第20个斐波那契数: {fibonacci(20)}")
    print("统计:", processor.get_stats())


if __name__ == "__main__":
    main()
