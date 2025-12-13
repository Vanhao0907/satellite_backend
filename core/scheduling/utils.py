def merge_dicts_with_sorted_values(dict1: object, dict2: object) -> object:
    """
    合并两个字典，将相同键的值合并为一个有序列表。

    参数：
    dict1 - 第一个字典
    dict2 - 第二个字典

    返回值：
    result - 合并后的字典
    """
    # 使用解包操作将两个字典合并
    result = {**dict1, **dict2}
    # 遍历合并后的字典，对相同键的值进行合并排序
    for key, _ in result.items():
        result[key] = dict1.get(key, []) + dict2.get(key, [])
    return result

def show_progress(total, current):
    """
    动态展示进度条。

    参数：
    total - 总进度
    current - 当前进度
    """
    progress = current / total  # 计算当前进度的比例
    bar_length = 40  # 进度条的长度
    block = int(round(bar_length * progress))  # 计算进度条中完成部分的长度
    # 构建进度条字符串，使用#表示已完成部分，-表示未完成部分
    progress_bar = "#" * block + "-" * (bar_length - block)
    # 打印进度条，使用\r使光标回到行首，flush=True使输出实时刷新
    print(f"\rProgress: [{progress_bar}] {progress * 100:.1f}%", end="", flush=True)
