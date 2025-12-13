"""
站内天线负载均衡辅助函数模块
用于在同一站点的多个天线中选择负载最低的天线
"""

import numpy as np


def calculate_antenna_load(antenna_task_count, antenna_time_usage, method='C', weight_task=0.3, weight_time=0.7):
    """
    计算天线负载指标

    参数：
    antenna_task_count - 天线已分配的任务数量数组 [num_antennas]
    antenna_time_usage - 天线已使用的时间数组（秒） [num_antennas]
    method - 负载计算方法：
             'A': 任务数量负载
             'B': 时间占用负载
             'C': 综合负载（推荐）
    weight_task - 任务数量权重（仅method='C'时使用）
    weight_time - 时间占用权重（仅method='C'时使用）

    返回值：
    load - 各天线的负载值（越小表示负载越轻）
    """
    if method == 'A':
        # 方案A：只考虑任务数量
        return antenna_task_count.copy()

    elif method == 'B':
        # 方案B：只考虑时间占用
        return antenna_time_usage.copy()

    elif method == 'C':
        # 方案C：综合负载（归一化后加权）
        # 归一化任务数量
        max_task = np.max(antenna_task_count) if np.max(antenna_task_count) > 0 else 1
        normalized_task = antenna_task_count / max_task

        # 归一化时间占用
        max_time = np.max(antenna_time_usage) if np.max(antenna_time_usage) > 0 else 1
        normalized_time = antenna_time_usage / max_time

        # 综合负载
        load = weight_task * normalized_task + weight_time * normalized_time
        return load

    else:
        # 默认使用方案A
        return antenna_task_count.copy()


def select_antenna_by_load(available_antennas, antenna_loads):
    """
    从可用天线中选择负载最低的天线

    参数：
    available_antennas - 可用天线的索引列表 [ant1, ant2, ...]
    antenna_loads - 所有天线的负载值数组

    返回值：
    selected_antenna - 选中的天线索引
    """
    if len(available_antennas) == 0:
        return None

    if len(available_antennas) == 1:
        return available_antennas[0]

    # 获取可用天线的负载值
    loads = [antenna_loads[ant] for ant in available_antennas]

    # 选择负载最小的天线
    min_load_idx = np.argmin(loads)
    selected_antenna = available_antennas[min_load_idx]

    return selected_antenna


def get_available_antennas(d1, sp_index, list_cm_avail, keys_line,
                           arr_all_end_time, end_time_cm_usage, end_lap_cm_usage):
    """
    获取某站点的所有可用天线列表

    参数：
    d1 - 站点索引
    sp_index - 当前圈次索引
    list_cm_avail - 各站点天线数量列表
    keys_line - 圈次键列表
    arr_all_end_time - 观测结束时间矩阵
    end_time_cm_usage - 天线使用结束时间矩阵
    end_lap_cm_usage - 天线上次使用圈次矩阵

    返回值：
    available_antennas - 可用天线索引列表
    antenna_end_times - 各天线的结束时间（用于后续计算开始时间）
    """
    available_antennas = []
    antenna_end_times = []

    antenna_count = list_cm_avail[d1]
    max_dd = end_lap_cm_usage.shape[1] - 1

    # 防止天线数量超限
    if antenna_count > (max_dd + 1):
        antenna_count = max_dd + 1

    for dd in range(antenna_count):
        if dd > max_dd:
            continue

        sp_index1 = end_lap_cm_usage[d1, dd]
        is_available = False
        end_time = 0

        if sp_index1 == 1e10:
            # 天线空闲
            if end_time_cm_usage[d1, dd] < (arr_all_end_time[d1, sp_index] - 300):
                is_available = True
                end_time = end_time_cm_usage[d1, dd]
        else:
            # 天线已被占用，检查间隔
            yp1 = keys_line[sp_index]
            yp2 = keys_line[int(sp_index1)]

            if yp1[:5] == yp2[:5]:  # 同一卫星
                if end_time_cm_usage[d1, dd] < (arr_all_end_time[d1, sp_index] - 300):
                    is_available = True
                    end_time = end_time_cm_usage[d1, dd]
            else:  # 不同卫星
                if end_time_cm_usage[d1, dd] < (arr_all_end_time[d1, sp_index] - 600):
                    is_available = True
                    end_time = end_time_cm_usage[d1, dd] + 300

        if is_available:
            available_antennas.append(dd)
            antenna_end_times.append(end_time)

    return available_antennas, antenna_end_times