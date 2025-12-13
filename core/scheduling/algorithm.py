import pandas as pd
from collections import defaultdict
import numpy as np
import copy
import itertools
from tqdm import tqdm
from utils import show_progress
from data_processing import process_df_utctime
from legacy_config import (INTRA_STATION_BALANCE, ANTENNA_LOAD_METHOD, LOAD_WEIGHT_TASK, LOAD_WEIGHT_TIME)

# ========== 站内天线负载均衡：全局变量 ==========
ANTENNA_TASK_COUNT = None  # [num_stations, max_antennas] - 天线任务数量统计
ANTENNA_TIME_USAGE = None  # [num_stations, max_antennas] - 天线时间占用统计
MAX_ANTENNAS = 20  # ========== 新增：系统支持的最大天线数 ==========


def calculate_antenna_load_score(antenna_task_count, antenna_time_usage, method='C'):
    """
    计算天线负载评分（越小表示负载越轻）
    """
    if method == 'A':
        return antenna_task_count.copy()
    elif method == 'B':
        return antenna_time_usage.copy()
    elif method == 'C':
        max_task = np.max(antenna_task_count) if np.max(antenna_task_count) > 0 else 1
        max_time = np.max(antenna_time_usage) if np.max(antenna_time_usage) > 0 else 1
        normalized_task = antenna_task_count / max_task
        normalized_time = antenna_time_usage / max_time
        return LOAD_WEIGHT_TASK * normalized_task + LOAD_WEIGHT_TIME * normalized_time
    else:
        return antenna_task_count.copy()


def calculate_load_penalty(antenna_load, max_load, station_avg_load):
    """
    计算天线的负载惩罚时间

    参数：
    antenna_load - 当前天线的负载（任务数或时间占用）
    max_load - 该站所有天线的最大负载
    station_avg_load - 该站的平均负载

    返回：
    penalty_time - 惩罚时间（秒），负载越高惩罚越大

    原理：
    - 负载低于平均：无惩罚或负惩罚（提前可用）
    - 负载等于平均：小惩罚
    - 负载高于平均：大惩罚
    - 负载接近最大：极大惩罚
    """
    if LOAD_AWARE_PENALTY != 'TRUE':
        return 0

    if max_load == 0:
        return 0

    # 计算负载比例（相对于最大负载）
    load_ratio = antenna_load / max(max_load, 1)

    # 计算负载偏离（相对于平均负载）
    if station_avg_load > 0:
        load_deviation = (antenna_load - station_avg_load) / station_avg_load
    else:
        load_deviation = 0

    if PENALTY_MODE == 'linear':
        # 线性惩罚：负载比例 × 惩罚系数
        penalty = load_ratio * PENALTY_FACTOR

    elif PENALTY_MODE == 'exponential':
        # 指数惩罚：让高负载天线的惩罚成倍增加
        # 使用 e^(2*load_ratio) - 1 作为惩罚曲线
        # load_ratio=0 → penalty=0
        # load_ratio=0.5 → penalty≈1.7倍
        # load_ratio=1.0 → penalty≈6.4倍
        import math
        penalty = (math.exp(2 * load_ratio) - 1) * PENALTY_FACTOR * 0.2

    elif PENALTY_MODE == 'adaptive':
        # 自适应惩罚：基于偏离程度
        if load_deviation > 0:
            # 高于平均：惩罚
            penalty = load_deviation * PENALTY_FACTOR
        else:
            # 低于平均：负惩罚（提前可用）
            penalty = load_deviation * PENALTY_FACTOR * 0.5
    else:
        penalty = load_ratio * PENALTY_FACTOR

    return penalty


def get_station_load_stats(d1):
    """
    获取站点的负载统计信息

    返回：
    max_load - 最大负载
    avg_load - 平均负载
    min_load - 最小负载
    """
    global ANTENNA_TASK_COUNT, ANTENNA_TIME_USAGE

    if ANTENNA_TASK_COUNT is None:
        return 0, 0, 0

    # 根据负载计算方法选择统计指标
    if ANTENNA_LOAD_METHOD == 'A':
        loads = ANTENNA_TASK_COUNT[d1, :]
    elif ANTENNA_LOAD_METHOD == 'B':
        loads = ANTENNA_TIME_USAGE[d1, :]
    else:
        # 综合负载
        task_loads = ANTENNA_TASK_COUNT[d1, :]
        time_loads = ANTENNA_TIME_USAGE[d1, :]
        loads = LOAD_WEIGHT_TASK * task_loads + LOAD_WEIGHT_TIME * time_loads

    max_load = np.max(loads)
    avg_load = np.mean(loads)
    min_load = np.min(loads)

    return max_load, avg_load, min_load


def initialize_antenna_load_tracking(num_stations):
    """初始化天线负载跟踪"""
    global ANTENNA_TASK_COUNT, ANTENNA_TIME_USAGE
    ANTENNA_TASK_COUNT = np.zeros((num_stations, 18))
    ANTENNA_TIME_USAGE = np.zeros((num_stations, 18))
    print(f"✓ 初始化天线负载跟踪：{num_stations}个站点 × 18根天线")


# ========== 负载感知可用性判断配置 ==========
LOAD_AWARE_PENALTY = 'TRUE'  # 启用负载感知惩罚
PENALTY_FACTOR = 150  # 惩罚系数（秒）：负载越高，虚拟延迟越大
PENALTY_MODE = 'exponential'  # 惩罚模式：'linear' 或 'exponential'


def set_balance_config(intra_balance='TRUE', method='C', weight_task=0.3, weight_time=0.7,
                       load_penalty='TRUE', penalty_factor=150, penalty_mode='exponential'):
    """设置负载均衡配置"""
    global INTRA_STATION_BALANCE, ANTENNA_LOAD_METHOD, LOAD_WEIGHT_TASK, LOAD_WEIGHT_TIME
    global LOAD_AWARE_PENALTY, PENALTY_FACTOR, PENALTY_MODE

    INTRA_STATION_BALANCE = intra_balance
    ANTENNA_LOAD_METHOD = method
    LOAD_WEIGHT_TASK = weight_task
    LOAD_WEIGHT_TIME = weight_time
    LOAD_AWARE_PENALTY = load_penalty
    PENALTY_FACTOR = penalty_factor
    PENALTY_MODE = penalty_mode

    if intra_balance == 'TRUE':
        print(f"✓ 站内天线负载均衡已启用 - 方法{method}")
        if method == 'C':
            print(f"  权重: 任务{weight_task:.1f} + 时间{weight_time:.1f}")

    if load_penalty == 'TRUE':
        print(f"✓ 负载感知惩罚已启用")
        print(f"  惩罚模式: {penalty_mode}")
        print(f"  惩罚系数: {penalty_factor}秒")


def count_time_station_num(dict_sat_laps_sta_time_all, keys_line, num_stations):
    """
    统计每一圈的开始结束时间、可观测地面站index和数量。

    参数：
    dict_sat_laps_sta_time_all - 包含每圈数据的字典
    keys_line - 每圈的键列表

    返回值：
    sat_dmz - 每圈可观测的地面站index列表
    sat_dmz_num - 每圈可观测的地面站数量
    arr_data_all_start_time - 每圈每个地面站观测的开始时间
    arr_data_all_end_time - 每圈每个地面站观测的结束时间
    """

    sat_dmz = []  # 存储每圈可观测的地面站index
    sat_dmz_num = []  # 存储每圈可观测的地面站数量
    arr_data_all_start_time = np.ones(
        (num_stations, len(dict_sat_laps_sta_time_all))) * 1e10  # 初始化每圈每个地面站的开始时间
    arr_data_all_end_time = np.zeros(
        (num_stations, len(dict_sat_laps_sta_time_all)))  # 初始化每圈每个地面站的结束时间
    arr_data_twice = np.zeros(
        (num_stations * 2, len(dict_sat_laps_sta_time_all) * 2))  # 存储多次观测的数据

    for key_index, list_value in enumerate(keys_line):
        sat_dmz_tmp = []  # 存储当前圈可观测的地面站index
        for v1 in dict_sat_laps_sta_time_all[list_value]:
            if v1[2] - v1[1] >= 300:  # 检查观测时间是否大于300秒
                if arr_data_all_start_time[v1[0] - 1, key_index] == 1e10:
                    # 存储开始时间
                    arr_data_all_start_time[v1[0] - 1, key_index] = v1[1]
                    sat_dmz_tmp.append(v1[0] - 1)
                else:
                    arr_data_twice[(v1[0] - 1) * 2, key_index *
                                   2] = arr_data_all_start_time[v1[0] - 1, key_index]
                if arr_data_all_end_time[v1[0] - 1, key_index] == 0:
                    # 存储结束时间
                    arr_data_all_end_time[v1[0] - 1, key_index] = v1[2]
                else:
                    arr_data_twice[(v1[0] - 1) * 2, key_index * 2 +
                                   1] = arr_data_all_end_time[v1[0] - 1, key_index]
                    arr_data_twice[(v1[0] - 1) * 2 + 1,
                    key_index * 2: key_index * 2 + 2] = v1[1:]
        sat_dmz.append(sat_dmz_tmp)
        sat_dmz_num.append(len(sat_dmz_tmp))

    return sat_dmz, sat_dmz_num, arr_data_all_start_time, arr_data_all_end_time


def data_joint(arr_all_start_time, arr_all_end_time, arr_sat_dmz_num):
    """
    数据合并，统计每圈的开始和结束时间，以及可观测地面站数量。

    参数：
    arr_all_start_time - 每圈每个地面站观测的开始时间
    arr_all_end_time - 每圈每个地面站观测的结束时间
    arr_sat_dmz_num - 每圈可观测的地面站数量

    返回值：
    mim_start_time_sort_add_end_time_add_dmz_num_add_lap - 每圈的开始时间、结束时间、地面站数量和圈数的组合
    min_start_time_sort_counts - 每个开始时间出现的次数
    """

    min_start_time_values = np.min(arr_all_start_time, axis=0)
    min_start_time_sort_index = np.argsort(min_start_time_values)
    mim_start_time_sort = min_start_time_values[min_start_time_sort_index]
    dmz_avial_num = arr_sat_dmz_num[min_start_time_sort_index]

    # 剔除重复值
    min_start_time_sort_unique, unique_index = np.unique(
        mim_start_time_sort, return_inverse=True)
    # 统计每个值重复出现的次数
    min_start_time_sort_counts = np.bincount(unique_index)

    max_end_time_values = np.max(arr_all_end_time, axis=0)
    max_end_time_sort_as_min = max_end_time_values[min_start_time_sort_index]

    mim_start_time_sort_add_end_num = np.hstack(
        (mim_start_time_sort.reshape(-1, 1), max_end_time_sort_as_min.reshape(-1, 1)))
    mim_start_time_sort_add_end_time_add_dmz_num = np.hstack(
        (mim_start_time_sort_add_end_num, dmz_avial_num.reshape(-1, 1)))
    mim_start_time_sort_add_end_time_add_dmz_num_add_lap = np.hstack(
        (mim_start_time_sort_add_end_time_add_dmz_num, min_start_time_sort_index.reshape(-1, 1)))
    mim_start_time_sort_add_end_time_add_dmz_num_add_lap = mim_start_time_sort_add_end_time_add_dmz_num_add_lap.astype(
        'int64')

    return mim_start_time_sort_add_end_time_add_dmz_num_add_lap, min_start_time_sort_counts


def cal_avail_dmz(list_cm_avail, keys_line, d1, sp_index, arr_data_all_end_time,
                  dmz_cm_use_end_time, dmz_cm_use_end_sp):
    """
    计算每个地面站可用的天线数量，以及每个天线的使用结束时间

    【改进版】集成负载感知的可用性判断：
    - 基础可用性：时间约束
    - 负载惩罚：高负载天线的虚拟延迟
    - 结果：高负载天线更难被判定为"可用"

    ========== 新增：边界检查 ==========
    """
    global ANTENNA_TASK_COUNT, ANTENNA_TIME_USAGE, MAX_ANTENNAS

    antenna_count = list_cm_avail[d1]

    # ========== 边界检查：不超过数组范围 ==========
    actual_max_antennas = dmz_cm_use_end_time.shape[1]
    antenna_count = min(antenna_count, actual_max_antennas)

    tmp_time = np.zeros(antenna_count)
    cm_avail_tmp = 0

    status = keys_line[sp_index][-5:]

    # 获取站点负载统计（用于计算惩罚）
    if LOAD_AWARE_PENALTY == 'TRUE' and ANTENNA_TASK_COUNT is not None:
        max_load, avg_load, min_load = get_station_load_stats(d1)
    else:
        max_load, avg_load, min_load = 0, 0, 0

    for dd in range(antenna_count):
        # ========== 边界检查：防止索引越界 ==========
        if dd >= actual_max_antennas:
            continue

        dmz_time = dmz_cm_use_end_time[d1, dd]
        start_time = max(dmz_time, arr_data_all_end_time[d1, sp_index])

        # ========== 基础可用性检查 ==========
        if dmz_cm_use_end_sp[d1, dd] == 1e10:
            # 天线从未使用过
            tmp_time[dd] = dmz_time
            cm_avail_tmp += 1
        else:
            lap_index = int(dmz_cm_use_end_sp[d1, dd])
            last_status = keys_line[lap_index][-5:]

            # 计算基础时间间隔
            if last_status == status:
                time_interval = 300  # 同卫星
            else:
                time_interval = 600  # 不同卫星

            # ========== 【核心改进】负载感知惩罚 ==========
            if LOAD_AWARE_PENALTY == 'TRUE' and ANTENNA_TASK_COUNT is not None:
                # 获取当前天线的负载
                if ANTENNA_LOAD_METHOD == 'A':
                    antenna_load = ANTENNA_TASK_COUNT[d1, dd]
                elif ANTENNA_LOAD_METHOD == 'B':
                    antenna_load = ANTENNA_TIME_USAGE[d1, dd]
                else:
                    antenna_load = (LOAD_WEIGHT_TASK * ANTENNA_TASK_COUNT[d1, dd] +
                                    LOAD_WEIGHT_TIME * ANTENNA_TIME_USAGE[d1, dd])

                # 计算负载惩罚（虚拟延迟）
                penalty = calculate_load_penalty(antenna_load, max_load, avg_load)

                # 应用惩罚：高负载天线需要更长的间隔才能"可用"
                effective_interval = time_interval + penalty
            else:
                effective_interval = time_interval

            # 使用调整后的间隔判断可用性
            if start_time >= dmz_time + effective_interval:
                tmp_time[dd] = dmz_time
                cm_avail_tmp += 1
            else:
                tmp_time[dd] = 1e20  # 标记为不可用

    return cm_avail_tmp, tmp_time


def save_use_plan(d1, s1, sp_index, arr_all_start_time, arr_all_end_time, d1_cm_end_time,
                  ground_station_cm_use_plan, ground_station_cm_use_plan_sort_by_start_time,
                  end_time_cm_usage, end_lap_cm_usage, status_index, qv_num):
    """
    存储使用方案（改进版：集成站内天线负载均衡）

    ========== 新增：边界检查 ==========
    """
    global ANTENNA_TASK_COUNT, ANTENNA_TIME_USAGE, MAX_ANTENNAS

    # 识别可用天线
    available_mask = d1_cm_end_time < 1e10
    available_indices = np.where(available_mask)[0]

    if len(available_indices) == 0:
        return (ground_station_cm_use_plan, ground_station_cm_use_plan_sort_by_start_time,
                end_time_cm_usage, end_lap_cm_usage)

    # 选择天线（核心改进）
    if INTRA_STATION_BALANCE == 'TRUE' and ANTENNA_TASK_COUNT is not None:
        # ========== 边界检查：确保不超过数组大小 ==========
        actual_max_antennas = ANTENNA_TASK_COUNT.shape[1]
        valid_indices = [idx for idx in available_indices if idx < actual_max_antennas]

        if not valid_indices:
            return (ground_station_cm_use_plan, ground_station_cm_use_plan_sort_by_start_time,
                    end_time_cm_usage, end_lap_cm_usage)

        station_loads = calculate_antenna_load_score(
            ANTENNA_TASK_COUNT[d1, :], ANTENNA_TIME_USAGE[d1, :], method=ANTENNA_LOAD_METHOD)
        available_loads = station_loads[valid_indices]
        min_load_idx = np.argmin(available_loads)
        cm_1 = valid_indices[min_load_idx]
    else:
        cm_xxx = np.argsort(d1_cm_end_time)
        cm_1 = cm_xxx[0]

    # 计算任务时间
    dmz_time = d1_cm_end_time[cm_1]
    start_time = max(dmz_time, arr_all_start_time[d1, sp_index])
    end_time = start_time + 300
    if status_index != 'climb':
        end_time = arr_all_end_time[d1, sp_index]

    # 计算状态匹配标志
    p = 1e10
    if status_index == 'climb':
        p = 1 if d1 >= qv_num else 0
    if status_index != 'climb':
        p = 3 if d1 < qv_num else 2

    # 保存分配方案
    ground_station_cm_use_plan[sp_index, 0] = d1 + 1
    ground_station_cm_use_plan[sp_index, 1] = cm_1 + 1
    ground_station_cm_use_plan[sp_index, 2] = start_time
    ground_station_cm_use_plan[sp_index, 3] = end_time
    ground_station_cm_use_plan[sp_index, 4] = p

    ground_station_cm_use_plan_sort_by_start_time[s1, 0] = d1 + 1
    ground_station_cm_use_plan_sort_by_start_time[s1, 1] = cm_1 + 1
    ground_station_cm_use_plan_sort_by_start_time[s1, 2] = start_time
    ground_station_cm_use_plan_sort_by_start_time[s1, 3] = end_time
    ground_station_cm_use_plan_sort_by_start_time[s1, 4] = p

    # 更新天线状态
    end_time_cm_usage[d1, cm_1] = end_time
    end_lap_cm_usage[d1, cm_1] = sp_index

    # ========== 更新负载统计（带边界检查） ==========
    if ANTENNA_TASK_COUNT is not None and cm_1 < ANTENNA_TASK_COUNT.shape[1]:
        ANTENNA_TASK_COUNT[d1, cm_1] += 1
        ANTENNA_TIME_USAGE[d1, cm_1] += (end_time - start_time)

    return (ground_station_cm_use_plan, ground_station_cm_use_plan_sort_by_start_time,
            end_time_cm_usage, end_lap_cm_usage)


def reallocate_parameter(mim_start_time_sort_add_end_time_add_dmz_num_add_lap, sat_dmz, s1, sp_index,
                         dmz_cm_use_plan_after_sort):
    """
    重新分配参数，找出需要重新分配的圈数和地面站。

    参数：
    mim_start_time_sort_add_end_time_add_dmz_num_add_lap - 每圈的开始时间、结束时间、地面站数量和圈数的组合
    sat_dmz - 每圈可观测的地面站index列表
    s1 - 当前分配次数
    sp_index - 当前圈数的index
    dmz_cm_use_plan_after_sort - 按开始时间排列的使用方案数组

    返回值：
    list_reallocate - 需要重新分配的圈数列表
    list_reallocate_sat_dmz - 需要重新分配的地面站列表
    """

    sp_1 = mim_start_time_sort_add_end_time_add_dmz_num_add_lap[s1 - 1, -1]
    sd_1 = sat_dmz[sp_1]
    sd_2 = sat_dmz[sp_index]
    end_max_time_1 = mim_start_time_sort_add_end_time_add_dmz_num_add_lap[s1, 1]
    list_reallocate = [s1]
    for s11 in range(s1):
        if dmz_cm_use_plan_after_sort[s1 - s11, -1] >= mim_start_time_sort_add_end_time_add_dmz_num_add_lap[s1, 1] - 600 \
                and dmz_cm_use_plan_after_sort[s1 - s11, -1] != 1e10 and dmz_cm_use_plan_after_sort[
            s1 - s11, -1] != 1e20:
            list_reallocate.append(s1 - s11)
    list_reallocate = list(range(list_reallocate[-1], s1 + 1))
    list_reallocate_sat_dmz = []
    for l_r in list_reallocate:
        sp_tmp = mim_start_time_sort_add_end_time_add_dmz_num_add_lap[l_r, -1]
        list_reallocate_sat_dmz.append(sat_dmz[sp_tmp])

    return list_reallocate, list_reallocate_sat_dmz


def reallocate(mim_start_time_sort_add_end_time_add_dmz_num_add_lap, list_reallocate, list_reallocate_sat_dmz,
               dmz_cm_use_plan, dmz_cm_use_plan_after_sort, sp_index, s1, list_cm_avail, keys_line,
               arr_data_all_end_time,
               dmz_cm_use_end_time_all, dmz_cm_use_end_sp_all, arr_data_all_start_time):
    """
    重新分配资源，解决时间冲突。

    参数：
    mim_start_time_sort_add_end_time_add_dmz_num_add_lap - 每圈的开始时间、结束时间、地面站数量和圈数的组合
    list_reallocate - 需要重新分配的圈数列表
    list_reallocate_sat_dmz - 需要重新分配的地面站列表
    dmz_cm_use_plan - 存储使用方案的数组
    dmz_cm_use_plan_after_sort - 按开始时间排列的使用方案数组
    sp_index - 当前圈数的index
    s1 - 当前分配次数
    list_cm_avail - 每个基站的天线数量列表
    keys_line - 每圈的键列表
    arr_data_all_end_time - 每圈每个地面站观测的结束时间
    dmz_cm_use_end_time_all - 每个天线的使用结束时间
    dmz_cm_use_end_sp_all - 每个天线上一轮观测的卫星圈数index
    arr_data_all_start_time - 每圈每个地面站观测的开始时间

    返回值：
    flagx - 是否成功重新分配的标志
    list_reallocate_tmp - 重新分配后的圈数列表
    dmz_cm_use_end_time_x2_tmp - 重新分配后的天线使用结束时间
    dmz_cm_use_end_sp_x2_tmp - 重新分配后的天线使用结束时间对应的圈数index
    use_plan - 重新分配后的使用方案
    """
    dmz_cm_use_end_time_x2_tmp = 0  # 初始化为0
    dmz_cm_use_end_sp_x2_tmp = 0  # 同步初始化关联变量
    use_plan = None

    num_stations = len(list_cm_avail)  # 获取地面站数量
    cm1 = -1
    time_end = np.zeros(8)
    list_reallocate_tmp = []
    flagx = 0

    for x1 in range(len(list_reallocate_sat_dmz) - 2, -1, -1):
        list_reallocate_sat_dmz_tmp = list_reallocate_sat_dmz[x1:]
        combinations = itertools.product(*list_reallocate_sat_dmz_tmp)
        ypp1 = list(combinations)
        if len(ypp1) == 1:
            dmz_cm_use_plan[sp_index, :] = 1e20
            dmz_cm_use_plan_after_sort[s1, :] = 1e20
            continue
        else:
            for x2 in ypp1:
                s1_tmp = list_reallocate[- len(x2)]
                list_reallocate_tmp = list_reallocate[- len(x2):]
                dmz_cm_use_end_time_tmp = copy.deepcopy(
                    dmz_cm_use_end_time_all[s1_tmp * num_stations - num_stations:s1_tmp * num_stations])
                dmz_cm_use_end_sp_tmp = copy.deepcopy(
                    dmz_cm_use_end_sp_all[s1_tmp * num_stations - num_stations:s1_tmp * num_stations])
                dmz_cm_use_end_time_x2_tmp = np.zeros(
                    (len(x2) * num_stations, 8))
                dmz_cm_use_end_sp_x2_tmp = np.zeros(
                    (len(x2) * num_stations, 8))
                use_plan = np.zeros((len(x2), 5))
                count1 = 0
                flag = 1
                for x2_id, x2_v in enumerate(x2):
                    if x2_id != len(x2) - 1 and x2_v in list_reallocate_sat_dmz[-1] and len(
                            list_reallocate_sat_dmz[x2_id - len(x2)]) > 1:
                        flag = 0
                        break
                if flag == 0:
                    continue
                for x2_id, x2_v in enumerate(x2):
                    sp_index1 = mim_start_time_sort_add_end_time_add_dmz_num_add_lap[
                        list_reallocate_tmp[x2_id], -1]
                    cm1, time_end = cal_avail_dmz(list_cm_avail, keys_line, x2_v, sp_index1, arr_data_all_end_time,
                                                  dmz_cm_use_end_time_tmp, dmz_cm_use_end_sp_tmp)
                    if cm1 == 0:
                        break
                    else:
                        cm_xxx = np.argsort(time_end)
                        dmz_time = time_end[cm_xxx[0]]
                        start_time = max(
                            dmz_time, arr_data_all_start_time[x2_v, sp_index1])
                        end_time = start_time + 300
                        cm_1 = cm_xxx[0]
                        use_plan[x2_id, 0] = x2_v + 1
                        use_plan[x2_id, 1] = cm_1 + 1
                        use_plan[x2_id, 2] = start_time
                        use_plan[x2_id, 3] = end_time
                        use_plan[x2_id, 4] = sp_index1
                        dmz_cm_use_end_time_tmp[x2_v, cm_1] = end_time
                        dmz_cm_use_end_sp_tmp[x2_v, cm_1] = sp_index
                    dmz_cm_use_end_time_x2_tmp[x2_id * num_stations: x2_id * num_stations + len(
                        list_cm_avail), :] = dmz_cm_use_end_time_tmp[:num_stations, :]
                    dmz_cm_use_end_sp_x2_tmp[x2_id * num_stations: x2_id * num_stations + len(
                        list_cm_avail), :] = dmz_cm_use_end_sp_tmp[:num_stations, :]
                if count1 == len(x2):
                    flagx = 1
                    break
            if flagx == 1:
                break

    return flagx, list_reallocate_tmp, dmz_cm_use_end_time_x2_tmp, dmz_cm_use_end_sp_x2_tmp, use_plan


def iterative_optimization(end_time_ground_station_num_lap_sort_by_start_time, ground_station_cm_use_plan,
                           ground_station_cm_use_plan_sort_by_start_time, sp_index, s1, list_cm_avail, keys_line,
                           arr_all_end_time, end_time_cm_usage_all, end_lap_cm_usage_all, arr_all_start_time,
                           satellite_ground_station, end_time_cm_usage, end_lap_cm_usage):
    """
    迭代优化，解决当前圈次无法分配地面站的问题。

    参数：
    end_time_ground_station_num_lap_sort_by_start_time - 按开始时间排序的圈次信息
    ground_station_cm_use_plan - 存储使用方案的数组
    ground_station_cm_use_plan_sort_by_start_time - 按开始时间排序的使用方案数组
    sp_index - 当前圈数的index
    s1 - 当前分配次数
    list_cm_avail - 每个基站的天线数量列表
    keys_line - 每圈的键列表
    arr_all_end_time - 每圈每个地面站观测的结束时间
    end_time_cm_usage_all - 每个天线的使用结束时间
    end_lap_cm_usage_all - 每个天线上一轮观测的卫星圈数index
    arr_all_start_time - 每圈每个地面站观测的开始时间
    satellite_ground_station - 每圈可观测的地面站index列表
    end_time_cm_usage - 每个天线的使用结束时间
    end_lap_cm_usage - 每个天线上一轮观测的卫星圈数index

    返回值：
    end_time_cm_usage - 更新后的每个天线的使用结束时间
    end_lap_cm_usage - 更新后的每个天线上一轮观测的卫星圈数index
    """

    num_stations = len(list_cm_avail)  # 获取地面站数量

    if ground_station_cm_use_plan_sort_by_start_time[s1, 0] == 1e10:
        list_reallocate, list_reallocate_sat_dmz = reallocate_parameter(
            end_time_ground_station_num_lap_sort_by_start_time, satellite_ground_station, s1, sp_index,
            ground_station_cm_use_plan_sort_by_start_time)
        flagx, list_reallocate_tmp, dmz_cm_use_end_time_reallocate, dmz_cm_use_end_sp_reallocate, use_plan_reallocate = \
            reallocate(end_time_ground_station_num_lap_sort_by_start_time, list_reallocate, list_reallocate_sat_dmz,
                       ground_station_cm_use_plan, ground_station_cm_use_plan_sort_by_start_time, sp_index, s1,
                       list_cm_avail, keys_line, arr_all_end_time, end_time_cm_usage_all, end_lap_cm_usage_all,
                       arr_all_start_time)
        if flagx == 1:
            for x3_id, x3_v in enumerate(list_reallocate_tmp):
                end_time_cm_usage_all[x3_v * num_stations:x3_v * num_stations +
                                                          num_stations] = dmz_cm_use_end_time_reallocate[
                                                                          x3_id * num_stations:x3_id * num_stations + num_stations]
                end_lap_cm_usage_all[x3_v * num_stations:x3_v * num_stations +
                                                         num_stations] = dmz_cm_use_end_sp_reallocate[
                                                                         x3_id * num_stations:x3_id * num_stations + num_stations]

                sp_index3 = int(use_plan_reallocate[x3_id, -1])
                ground_station_cm_use_plan[sp_index3,
                :] = use_plan_reallocate[x3_id, :4]
                ground_station_cm_use_plan_sort_by_start_time[x3_v,
                :] = use_plan_reallocate[x3_id, :4]
            end_time_cm_usage1 = dmz_cm_use_end_time_reallocate[-num_stations:, :]
            end_lap_cm_usage1 = dmz_cm_use_end_sp_reallocate[-num_stations:, ]
            return end_time_cm_usage1, end_lap_cm_usage1

    return end_time_cm_usage, end_lap_cm_usage


def cal_success_rate(ground_station_cm_use_plan_sort_by_start_time, dict_sat_laps_sta_time_all):
    """
    计算分配成功率。
    参数：
    ground_station_cm_use_plan_sort_by_start_time - 按开始时间排序的使用方案数组
    dict_sat_laps_sta_time_all - 包含每圈数据的字典
    返回值：
    success_rate11 - 包含本身不够分配时间的样本的成功率
    success_rate22 - 剔除本身不够分配时间的样本的成功率
    climb_S - climb状态的成功率（处理除零）
    operation_S - operation状态的成功率（处理除零）
    """
    less_than_300s_data_wrong = []
    allocate_fail = []
    allocate_fail_data_wrong = []
    allocate_success = []
    num2 = 0
    climb_success = 0
    climb_fail = 0
    operation_success = 0
    operation_fail = 0

    for i in ground_station_cm_use_plan_sort_by_start_time:
        if i[0] == 1234567890:
            less_than_300s_data_wrong.append(num2)
        if i[0] == 1e10:
            allocate_fail.append(num2)
        if i[0] == 1e20:
            allocate_fail_data_wrong.append(num2)
        if i[0] != 1234567890 and i[0] != 1e10 and i[0] != 1e20:
            allocate_success.append(num2)
        if i[-1] == 0:
            climb_fail += 1
        if i[-1] == 1:
            climb_success += 1
        if i[-1] == 2:
            operation_fail += 1
        if i[-1] == 3:
            operation_success += 1
        num2 += 1

    # 计算成功率（核心修改：处理除零）
    success_rate22 = len(allocate_success) / (
            len(dict_sat_laps_sta_time_all) - len(less_than_300s_data_wrong) - len(allocate_fail_data_wrong))
    success_rate11 = len(allocate_success) / len(dict_sat_laps_sta_time_all)

    # 处理 climb 状态成功率（分母为0时返回0或NaN）
    climb_total = climb_success + climb_fail
    climb_S = climb_success / climb_total if climb_total != 0 else 0  # 或用 np.nan 表示无数据

    # 处理 operation 状态成功率（同理）
    operation_total = operation_success + operation_fail
    operation_S = operation_success / operation_total if operation_total != 0 else 0  # 或用 np.nan 表示无数据

    return success_rate11, success_rate22, climb_S, operation_S


def check_crossover_overflow(list_cm_avail, ground_station_cm_use_plan, arr_all_start_time, arr_all_end_time):
    """
    检查天线使用时间是否存在交叠或超出可观测时间。

    参数：
    list_cm_avail - 每个基站的天线数量列表
    ground_station_cm_use_plan - 存储使用方案的数组
    arr_all_start_time - 每圈每个地面站观测的开始时间
    arr_all_end_time - 每圈每个地面站观测的结束时间

    ========== 修改：增强边界检查 ==========
    """

    flag = 1
    for i in range(len(list_cm_avail)):
        j = list_cm_avail[i]
        # ========== 新增：处理天线数量超过系统限制的情况 ==========
        if j > MAX_ANTENNAS:
            j = MAX_ANTENNAS
            print(f"检查时已将地面站{i}的天线数量截断为{MAX_ANTENNAS}")

        for k in range(j):
            list_check_start_time = []
            list_check_end_time = []
            list_x = []
            for u_p_n in range(ground_station_cm_use_plan.shape[0]):
                use_plan_line = ground_station_cm_use_plan[u_p_n]
                if use_plan_line[0] == i + 1 and use_plan_line[1] == k + 1:
                    list_check_start_time.append(use_plan_line[2])
                    list_check_end_time.append(use_plan_line[3])
                    list_x.append(u_p_n)
            # 为空时直接跳过后续检查
            if not list_check_start_time:
                continue

            arr_check_start_time = np.array(list_check_start_time)
            arr_check_end_time = np.array(list_check_end_time)
            arr_x = np.array(list_x, dtype=int)

            # 计算排序索引
            arr_check_start_time_sort = np.argsort(arr_check_start_time)

            # 定义排序后的开始时间数组
            arr_check_start_time_after_sort = arr_check_start_time[arr_check_start_time_sort]
            arr_check_end_time_after_sort = arr_check_end_time[arr_check_start_time_sort]
            arr_x_after_sort = arr_x[arr_check_start_time_sort].astype(int)

            # 索引有效性检查
            if (arr_x_after_sort < 0).any() or (arr_x_after_sort >= arr_all_start_time.shape[1]).any():
                print(f"警告：地面站{i}天线{k}存在无效索引，已跳过检查")
                continue

            arr_data_all_start_time1 = arr_all_start_time[i, arr_x_after_sort]
            arr_data_all_end_time1 = arr_all_end_time[i, arr_x_after_sort]

            # 现在可以安全使用arr_check_start_time_after_sort变量
            for ii in range(len(arr_check_start_time_after_sort)):
                if (arr_check_start_time_after_sort[ii] >= arr_data_all_start_time1[ii] and
                        arr_check_end_time_after_sort[ii] <= arr_data_all_end_time1[ii]):
                    continue
                else:
                    flag = 0
                    break
            if flag != 1:
                break

            # 检查时间交叠
            ypp = arr_check_start_time_after_sort[1:] - arr_check_end_time_after_sort[:-1]
            for ii in ypp:
                if ii >= 0:
                    continue
                else:
                    flag = 2
                    break
            if flag != 1:
                break
        if flag != 1:
            break

    if flag == 0:
        print('验算结论：存在超出可观测时间的情况')
    elif flag == 1:
        print('验算结论：观测时间分配合理，无超出可观测时间的情况，同一天线无时间交错的情况')
    elif flag == 2:
        print('验算结论：同一天线存在时间交错的情况')


def answer_type_transform(keys_line, ground_station_cm_use_plan, all_data):
    """
    将答案转成适合存入Excel的形式。

    参数：
    keys_line - 每圈的键列表
    ground_station_cm_use_plan - 存储使用方案的数组
    all_data - 所有数据的列表

    返回值：
    results - 转换后的答案列表
    """

    sta_num = len(all_data)
    results = []

    # 预处理数据，创建索引
    all_dfs = []
    index_dict = defaultdict(dict)

    for i in range(sta_num):
        key = list(all_data[i].keys())[0]
        info = all_data[i][key]

        for j, df in enumerate(info):
            df['start_timestamp'], df['stop_timestamp'] = process_df_utctime(
                df).T
            df['antenna'] = j
            all_dfs.append(df)
            index_dict[(key, j)] = df

    for i in range(sta_num):
        key = list(all_data[i].keys())[0]
        antenna_num = len(all_data[i][key])
        row_num = len(all_data[i][key][0])
        answer_array = (np.ones((row_num, antenna_num)) * 11).astype("int64")
        results.append(answer_array.astype("str"))

    for answer_index, (sat, laps, status) in tqdm(enumerate([item.split('-') for item in keys_line])):
        # show_progress(len(keys_line), answer_index)

        # 获取分配信息
        sta_index = int(ground_station_cm_use_plan[answer_index][0]) - 1
        antenna_index = int(ground_station_cm_use_plan[answer_index][1]) - 1
        start_allocation_time = ground_station_cm_use_plan[answer_index][2]
        stop_allocation_time = ground_station_cm_use_plan[answer_index][3]
        qv_s_allocation_flag = ground_station_cm_use_plan[answer_index][4]

        if ground_station_cm_use_plan[answer_index][0] <= sta_num:
            key = list(all_data[sta_index].keys())[0]
            df = index_dict[(key, antenna_index)]

            condition = (df['sat'] == sat) & (df['laps'] == int(laps)) & (df['Status'] == str(status))
            matching_indices = df.index[condition].tolist()

            for idx in matching_indices:
                start_time = df.at[idx, 'start_timestamp']
                stop_time = df.at[idx, 'stop_timestamp']

                if (start_allocation_time - start_time < 0) and (stop_time - stop_allocation_time < 0):
                    results[sta_index][(idx, antenna_index)] = "13"
                elif (start_allocation_time - start_time) <= 1:
                    results[sta_index][(idx, antenna_index)] = "02"
                elif (stop_time - stop_allocation_time) <= 1:
                    results[sta_index][(idx, antenna_index)] = "03"
                elif qv_s_allocation_flag == 0:
                    results[sta_index][(idx, antenna_index)] = "14"
                elif qv_s_allocation_flag == 2:
                    results[sta_index][(idx, antenna_index)] = "15"
                else:
                    results[sta_index][(idx, antenna_index)] = "04"
        else:
            for i in range(sta_num):
                key = list(all_data[i].keys())[0]
                info = all_data[i][key]

                for df in info:
                    condition = (df['sat'] == sat) & (df['laps'] == int(laps)) & (df['Status'] == str(status))
                    matching_indices = df.index[condition].tolist()

                    for idx in matching_indices:
                        if ground_station_cm_use_plan[answer_index].any() == 1234567890:
                            results[sta_index][(idx, antenna_index)] = "12"
                        elif ground_station_cm_use_plan[answer_index].any() >= 10e10:
                            results[sta_index][(idx, antenna_index)] = "13"
    return results


def resorted_by_status(status, QV_num, ground_station_start_time_in_one_lap_sorted1,
                       ground_station_start_time_in_one_lap_sorted2,
                       ground_station_start_time_in_one_lap_sorted3):
    s_list1, s_list2, s_list3 = [], [], []
    qv_list1, qv_list2, qv_list3 = [], [], []
    for x1 in ground_station_start_time_in_one_lap_sorted1:
        if x1 >= QV_num:
            s_list1.append(x1)
        else:
            qv_list1.append(x1)
    for x2 in ground_station_start_time_in_one_lap_sorted2:
        if x2 >= QV_num:
            s_list2.append(x2)
        else:
            qv_list2.append(x2)
    for x3 in ground_station_start_time_in_one_lap_sorted3:
        if x3 >= QV_num:
            s_list3.append(x3)
        else:
            qv_list3.append(x3)
    if status == 'Climb':
        return s_list1 + qv_list1, s_list2 + qv_list2, s_list3 + qv_list3
    else:
        return qv_list1 + s_list1, qv_list2 + s_list2, qv_list3 + s_list3