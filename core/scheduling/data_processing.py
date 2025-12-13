import os
import pandas as pd
import numpy as np
from collections import defaultdict
from utils import merge_dicts_with_sorted_values


def read_multiple_csv_files_return_data(root_folder):
    """
    读取根目录下所有CSV文件并返回数据。

    参数：
    root_folder - 根目录路径

    返回值：
    all_data - 包含每个文件夹数据的列表
    """
    all_data = []

    # 检查根文件夹是否存在
    if not os.path.exists(root_folder):
        print(f"Warning: Root folder '{root_folder}' does not exist. Skipping this path.")
        return all_data # 如果根文件夹不存在，直接返回空列表

    for folder_name in os.listdir(root_folder):
        folder_path = os.path.join(root_folder, folder_name)
        if os.path.isdir(folder_path):
            print(f"Reading files from folder: {folder_name}")
            folder_data = []
            for file_name in os.listdir(folder_path):
                if file_name.endswith('.csv'):
                    file_path = os.path.join(folder_path, file_name)
                    # 单个 CSV 文件损坏或无法读取时，跳过该文件并打印错误信息
                    try:
                        data = pd.read_csv(file_path)
                        print(f"Reading file: {file_name}")
                        folder_data.append(data)
                    except Exception as e:
                        print(f"Error reading file {file_name} in {folder_name}: {e}. Skipping this file.")
            if folder_data: # 只有当文件夹中有数据时才添加到 all_data
                all_data.append({folder_name: folder_data})
                print(f"================ {folder_name}")
            else:
                print(f"No CSV files found or errors occurred in folder: {folder_name}. Skipping this folder.")
    return all_data


def process_df_utctime(df):
    """
    将DataFrame中的UTC时间转换为时间戳。

    参数：
    df - 输入的DataFrame

    返回值：
    start_stop_time - 包含开始和结束时间戳的二维数组
    """

    # 匹配时间列名
    try:
        start_col = next(col for col in ['start(UTC)', 'start'] if col in df.columns)
    except StopIteration:
        raise ValueError("DataFrame中缺少'start(UTC)'或'start'列。")

    try:
        stop_col = next(col for col in ['stop(UTC)', 'stop'] if col in df.columns)
    except StopIteration:
        raise ValueError("DataFrame中缺少'stop(UTC)'或'stop'列。")

    # 将start(UTC)列转换为时间戳
    start_timestamp = pd.to_datetime(
        df[start_col]).astype('int64') // 10 ** 9
    # 将stop(UTC)列转换为时间戳
    stop_timestamp = pd.to_datetime(df[stop_col]).astype('int64') // 10 ** 9
    # 将开始和结束时间戳堆叠为二维数组
    start_stop_time = np.transpose(
        np.vstack((start_timestamp, stop_timestamp)))
    return start_stop_time


def read_data_dict(all_data):
    """
    读取数据字典，将所有地面站数据合并到一个字典中。

    参数：
    all_data - 包含所有地面站数据的列表

    返回值：
    dict_sat_laps_sta_time_all - 合并后的数据字典
    """
    dict_sat_laps_sta_time_all = {}
    num_sta = 0  # 初始化地面站编号

    # 定义列名优先级和别名
    col_mappings = {
        'sat_col': ['sat', 'Sat'],
        'laps_col': ['laps', 'Laps'],
        'status_col': ['Status', 'status']
    }

    for folder_data in all_data:
        num_sta += 1
        for folder_name, data_list in folder_data.items():
            print(f"Read data from folder: {folder_name}")
            data = data_list[0]

            # 动态确定实际的列名
            actual_cols = {}
            for key, potential_names in col_mappings.items():
                found_col = next((col for col in potential_names if col in data.columns), None)
                if found_col is None:
                    # 如果关键列缺失，根据业务需求选择抛出错误或跳过
                    raise ValueError(
                        f"Required column for {key} (any of {potential_names}) not found in DataFrame from folder: {folder_name}")
                actual_cols[key] = found_col

            # 使用动态确定的列名创建卫星圈次数据
            sat_laps_data = data.apply(
                lambda row: str(row[actual_cols['sat_col']]) + '-' +
                            str(row[actual_cols['laps_col']]) + '-' +
                            str(row[actual_cols['status_col']]),
                axis=1
            )
            sat_laps = list(np.array(sat_laps_data))

            # sat_status_data = data.apply(lambda row: str(row['Status']), axis=1)
            # sat_status = np.array(list(np.array(sat_status_data)))
            # sat_status = sat_status.reshape(-1, 1)
            # sat_status_index = []
            # for x in sat_status:
            #     if x == 'climb':
            #         sat_status_index.append(0)
            #     else:
            #         sat_status_index.append(1)

            # 将DataFrame中的UTC时间转换为时间戳
            start_stop_datatime_data = process_df_utctime(data)
            # 为每行数据添加地面站编号
            sta_flag = np.ones(
                (start_stop_datatime_data.shape[0], 1)) * num_sta
            # 将地面站编号与开始和结束时间堆叠为二维数组
            sta_flag_start_stop_datatime_data = np.hstack(
                    (sta_flag.astype('int64'), start_stop_datatime_data))
            # sta_flag_start_stop_datatime_data = np.hstack(
            #     (sat_status, sta_flag.astype('int64')))
            # sta_flag_start_stop_datatime_data = np.hstack(
            #     (sta_flag_start_stop_datatime_data, start_stop_datatime_data))
            # 将每一行数据转换为列表
            sta_laps_time = sta_flag_start_stop_datatime_data.tolist()
            dict_sat_laps_time = defaultdict(list)
            for key, value in zip(sat_laps, sta_laps_time):
                dict_sat_laps_time[key].append(value)
            # 将局部字典合并到全局字典中
            dict_sat_laps_time = dict(dict_sat_laps_time)
            dict_sat_laps_sta_time_all = merge_dicts_with_sorted_values(
                dict_sat_laps_sta_time_all, dict_sat_laps_time)
    return dict_sat_laps_sta_time_all
