def add_numbers(a, b):
    result = a + b
    return result


def multiply_numbers(a, b):
    result = 0
    for i in range(b):
        result = add_numbers(result, a)
    return result


def calculate_average(numbers):
    total = 0
    count = 0
    for n in numbers:
        total = add_numbers(total, n)
        count = count + 1
    if count == 0:
        return 0
    average = total / count
    return average


def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, n):
        if n % i == 0:
            return False
    return True


def main():
    nums = [2, 3, 5, 7, 11, 13]
    avg = calculate_average(nums)
    print("平均值:", avg)
    product = multiply_numbers(3, 4)
    print("3 乘 4 =", product)
    primes = [x for x in range(1, 20) if is_prime(x)]
    print("1到19中的素数:", primes)


if __name__ == "__main__":
    main()
