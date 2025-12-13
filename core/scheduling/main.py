import time
import os
import pandas as pd
import numpy as np
from datetime import datetime
from data_processing import read_multiple_csv_files_return_data, read_data_dict
from algorithm import (count_time_station_num, data_joint, cal_avail_dmz, save_use_plan,
                       iterative_optimization, cal_success_rate, check_crossover_overflow, answer_type_transform,
                       resorted_by_status,
                       initialize_antenna_load_tracking, set_balance_config,
                       iterative_optimization, cal_success_rate, check_crossover_overflow, answer_type_transform,
                       resorted_by_status)
from config import (ROOT_FOLDER, OPTIMIZATION, METHOD, ANSWER_TYPE, USE_SA, SA_MAX_TIME,
                    INTRA_STATION_BALANCE, ANTENNA_LOAD_METHOD, LOAD_WEIGHT_TASK, LOAD_WEIGHT_TIME)
from validate_results import validate_allocation_results
from simulated_annealing import optimize_with_sa


def main():
    start_time = time.time()

    # ========== 修改：只读取QV频段数据 ==========
    print("正在读取QV频段数据...")
    all_data = read_multiple_csv_files_return_data(ROOT_FOLDER)

    # 提取站点名称
    station_name = []
    for folder_data in all_data:
        station_name += list(folder_data.keys())

    # 获取各站点的天线数量列表
    list_cm_avail = [len(list(e.values())[0]) for e in all_data]

    # 获取地面站数量（现在只有QV的8个站）
    num_stations = len(list_cm_avail)

    # QV站点数量（用于resorted_by_status函数）
    # 由于现在只有QV站，QV_num = 总站数
    QV_num = len(all_data)
    # ========== 修改结束 ==========

    # 字典，每一圈各基站能观测的时间窗口
    dict_sat_laps_sta_time_all = read_data_dict(all_data)

    # ========== 初始化天线负载跟踪 ==========
    initialize_antenna_load_tracking(num_stations)
    set_balance_config(
        intra_balance=INTRA_STATION_BALANCE,
        method=ANTENNA_LOAD_METHOD,
        weight_task=LOAD_WEIGHT_TASK,
        weight_time=LOAD_WEIGHT_TIME
    )

    print("=" * 70)
    print("卫星资源调度系统 - 仅QV频段（站内天线负载均衡版）")
    print("=" * 70)
    print(f"配置信息:")
    print(f"  频段: QV")
    print(f"  站点数量: {num_stations}")
    print(f"  站点列表: {', '.join(station_name)}")
    print(f"  总天线数量: {sum(list_cm_avail)}")
    print(f"  各站天线数: {list_cm_avail}")
    print(f"  总圈次数量: {len(dict_sat_laps_sta_time_all)}")
    print(f"  分配策略METHOD: {METHOD}")
    print(f"  启用迭代优化: {OPTIMIZATION}")
    print(f"  站内天线负载均衡: {INTRA_STATION_BALANCE}")
    if INTRA_STATION_BALANCE == 'TRUE':
        print(f"    负载计算方法: {ANTENNA_LOAD_METHOD}")
        if ANTENNA_LOAD_METHOD == 'C':
            print(f"    权重配置: 任务{LOAD_WEIGHT_TASK}, 时间{LOAD_WEIGHT_TIME}")
    print("=" * 70 + "\n")

    # 将字典的键放在一行，使用空格作为分隔符
    keys_line = list(dict_sat_laps_sta_time_all.keys())

    # satellite_ground_station - 不同卫星圈数可被观测的地面站的index
    # satellite_ground_station_num - 不同卫星圈数可被观测的地面站数量
    # arr_all_start_time - 每个地面站观测不同卫星圈数的开始时间
    # arr_all_end_time - 每个地面站观测不同卫星圈数的结束时间
    satellite_ground_station, satellite_ground_station_num, arr_all_start_time, arr_all_end_time = count_time_station_num(
        dict_sat_laps_sta_time_all, keys_line, num_stations)

    # end_time_ground_station_num_lap_sort_by_start_time - 按照每一圈的开始时间排序，再开始时间顺序，统计结束时间、可观测地面站数量、当前圈的index
    # count_sorted_start_time_same - 按开始时间排序后，统计开始时间重复的圈的数量
    end_time_ground_station_num_lap_sort_by_start_time, count_sorted_start_time_same = data_joint(
        arr_all_start_time, arr_all_end_time, np.array(satellite_ground_station_num))

    # end_time_cm_usage - 存储每个天线的使用结束时间
    # end_lap_cm_usage - 存储每个天线上一轮观测的卫星圈数index
    # end_time_cm_usage = np.zeros((num_stations, 18))
    end_time_cm_usage = np.random.uniform(-100, 0, (num_stations, 18))
    end_lap_cm_usage = np.ones((num_stations, 18)) * 1e10

    # 存储使用方案，地面站、天线、开始时间、结束时间、资源使用是否与状态匹配（0：不匹配，1：匹配）
    ground_station_cm_use_plan = np.ones(
        (len(dict_sat_laps_sta_time_all), 5)) * 1e10

    # 存储使用方案，地面站、天线、开始时间、结束时间（按照开始时间排列）
    ground_station_cm_use_plan_sort_by_start_time = np.ones(
        (len(dict_sat_laps_sta_time_all), 5)) * 1e10

    count1 = 0
    s1 = -1
    # end_time_cm_usage_all - 存储每个天线的使用结束时间，为后续迭代做准备
    # end_lap_cm_usage_all - 存储每个天线观测的卫星圈数index，为后续迭代做准备
    end_time_cm_usage_all = np.zeros(
        (num_stations * len(dict_sat_laps_sta_time_all), 18))
    end_lap_cm_usage_all = np.zeros(
        (num_stations * len(dict_sat_laps_sta_time_all), 18))
    arr_cm_sum = np.zeros(num_stations)

    # ========== 【改进2-4】新增时间占用统计（优先级2改进） ==========
    arr_cm_time_occupancy = np.zeros(num_stations)  # 累计各站点的时间占用
    # ========== 【改进2-4结束】 ==========

    for i in range(len(count_sorted_start_time_same)):
        # 某一开始时间重复数量
        i_value = count_sorted_start_time_same[i]
        count1 += i_value
        for i1 in end_time_ground_station_num_lap_sort_by_start_time[count1 - i_value:count1]:
            # 当前圈的index
            sp_index = i1[3]
            # 统计当前分配次数
            s1 += 1
            # 判断当前圈观测时间是否小300s，在前面统计开始和结束时间时，将观测时间小于300s的圈数的开始和结束时间都设置为1e10
            if i1[0] == 1e10:
                ground_station_cm_use_plan[sp_index] = 1234567890
                ground_station_cm_use_plan_sort_by_start_time[s1] = 1234567890
                continue

            # 当前圈可观测地面站数量
            sd = satellite_ground_station_num[i1[2]]
            if sd > 0:
                # 当前圈各地面站观测开启时间
                ground_station_start_time_in_one_lap = arr_all_start_time[:, sp_index]
                # 对当前圈各地面站观测开启时间排序，从早到晚
                arr_tmp_cm = np.zeros(num_stations)
                status = keys_line[sp_index][-5:]
                for d1 in range(num_stations):
                    if ground_station_start_time_in_one_lap[d1] != 1e10:
                        cm_a, _ = cal_avail_dmz(list_cm_avail, keys_line, d1, sp_index, arr_all_end_time,
                                                end_time_cm_usage, end_lap_cm_usage)
                        arr_tmp_cm[d1] = cm_a / list_cm_avail[d1]

                ground_station_start_time_in_one_lap_sorted1 = np.argsort(
                    ground_station_start_time_in_one_lap)
                ground_station_start_time_in_one_lap_sorted2 = np.argsort(
                    arr_tmp_cm)
                # ========== 【改进2-4】METHOD=3使用综合评分排序 ==========
                # 原来：ground_station_start_time_in_one_lap_sorted3 = np.argsort(arr_cm_sum)
                # 现在：综合考虑任务数量和时间占用
                if METHOD == 3:
                    # 归一化处理
                    arr_cm_sum_normalized = arr_cm_sum / (np.max(arr_cm_sum) + 1e-6)
                    arr_cm_time_normalized = arr_cm_time_occupancy / (np.max(arr_cm_time_occupancy) + 1e-6)

                    # 综合评分：30%任务数量 + 70%时间占用
                    arr_balanced_score = 0.3 * arr_cm_sum_normalized + 0.7 * arr_cm_time_normalized
                    ground_station_start_time_in_one_lap_sorted3 = np.argsort(arr_balanced_score)
                else:
                    # 其他方法保持原样
                    ground_station_start_time_in_one_lap_sorted3 = np.argsort(arr_cm_sum)
                # ========== 【改进2-4结束】 ==========

                # 考虑爬升和操作态
                if status.lower() == 'climb':
                    ground_station_cm_use_plan[sp_index, -1] = 0
                    ground_station_cm_use_plan_sort_by_start_time[s1, -1] = 0
                else:
                    ground_station_cm_use_plan[sp_index, -1] = 2
                    ground_station_cm_use_plan_sort_by_start_time[s1, -1] = 2
                ground_station_start_time_in_one_lap_sorted1_status, \
                    ground_station_start_time_in_one_lap_sorted2_status, \
                    ground_station_start_time_in_one_lap_sorted3_status = resorted_by_status(status, QV_num,
                                                                                             ground_station_start_time_in_one_lap_sorted1,
                                                                                             ground_station_start_time_in_one_lap_sorted2,
                                                                                             ground_station_start_time_in_one_lap_sorted3)

                for d0 in range(num_stations):
                    if METHOD == 1:
                        d1 = ground_station_start_time_in_one_lap_sorted1_status[d0]
                    elif METHOD == 2:
                        d1 = ground_station_start_time_in_one_lap_sorted2_status[d0]
                    else:
                        d1 = ground_station_start_time_in_one_lap_sorted3_status[d0]

                    if ground_station_start_time_in_one_lap[d1] == 1e10:
                        continue
                    else:
                        cm_a, d1_cm_end_time = cal_avail_dmz(list_cm_avail, keys_line, d1, sp_index,
                                                             arr_all_end_time,
                                                             end_time_cm_usage, end_lap_cm_usage)
                        if cm_a <= 0:
                            continue

                        # 存储使用方案
                        ground_station_cm_use_plan, ground_station_cm_use_plan_sort_by_start_time, end_time_cm_usage, end_lap_cm_usage = \
                            save_use_plan(d1, s1, sp_index, arr_all_start_time, arr_all_end_time, d1_cm_end_time,
                                          ground_station_cm_use_plan, ground_station_cm_use_plan_sort_by_start_time,
                                          end_time_cm_usage, end_lap_cm_usage, keys_line[sp_index][-5:], QV_num)
                        break

                # 存储每个天线的使用结束时间，为后续迭代做准备
                # 存储每个天线观测的卫星圈数index，为后续迭代做准备
                end_time_cm_usage_all[s1 * num_stations:s1 *
                                                        num_stations + num_stations, :] = end_time_cm_usage.copy()
                end_lap_cm_usage_all[s1 * num_stations:s1 *
                                                       num_stations + num_stations, :] = end_lap_cm_usage.copy()

                if OPTIMIZATION == 'TRUE':
                    # 迭代优化，找出可能导致当前圈观测的圈数，再结合当前圈一起重新分配
                    end_time_cm_usage, end_lap_cm_usage = iterative_optimization(
                        end_time_ground_station_num_lap_sort_by_start_time,
                        ground_station_cm_use_plan, ground_station_cm_use_plan_sort_by_start_time,
                        sp_index, s1, list_cm_avail, keys_line, arr_all_end_time, end_time_cm_usage_all,
                        end_lap_cm_usage_all, arr_all_start_time, satellite_ground_station,
                        end_time_cm_usage, end_lap_cm_usage)

                # if ground_station_cm_use_plan_sort_by_start_time[s1, 0] < 10:
                #    arr_cm_sum[int(
                #        ground_station_cm_use_plan_sort_by_start_time[s1, 0]) - 1] += 1
                # ========== 【改进2-4】更新任务数量和时间占用统计 ==========
                if ground_station_cm_use_plan_sort_by_start_time[s1, 0] < 10:
                    station_idx = int(ground_station_cm_use_plan_sort_by_start_time[s1, 0]) - 1
                    arr_cm_sum[station_idx] += 1

                    # 新增：累计时间占用
                    task_start = ground_station_cm_use_plan_sort_by_start_time[s1, 2]
                    task_end = ground_station_cm_use_plan_sort_by_start_time[s1, 3]
                    if task_start < 1e10 and task_end < 1e10:
                        task_duration = task_end - task_start
                        arr_cm_time_occupancy[station_idx] += task_duration
                # ========== 【改进2-4结束】 ==========

    answer_info = np.array([item.split('-') for item in keys_line])
    ground_station_cm_use_plan_withlaps = np.hstack(
        (answer_info, ground_station_cm_use_plan))

    # 保存为二进制文件
    if OPTIMIZATION == "TRUE":
        np.save('data1_opt_{}.npy'.format(METHOD),
                ground_station_cm_use_plan_withlaps)
    else:
        np.save('data1_{}.npy'.format(METHOD),
                ground_station_cm_use_plan_withlaps)

    # 计算成功率
    success_rate = cal_success_rate(
        ground_station_cm_use_plan_sort_by_start_time, dict_sat_laps_sta_time_all)
    if OPTIMIZATION == 'TRUE':
        print('方法{}，迭代优化后观测成功率(包含本身不够分配时间的样本): {}'.format(
            METHOD, success_rate[0]))
        print('方法{}，迭代优化后观测成功率(剔除本身不够分配时间的样本): {}'.format(
            METHOD, success_rate[1]))

        print('方法{}，迭代优化后climb状态观测成功率(包含本身不够分配时间的样本): {}'.format(
            METHOD, success_rate[2]))
        print('方法{}，迭代优化后operation状态观测成功率(剔除本身不够分配时间的样本): {}'.format(
            METHOD, success_rate[3]))
    else:
        print('方法{}，未迭代优化观测成功率(包含本身不够分配时间的样本): {}'.format(
            METHOD, success_rate[0]))
        print('方法{}，未迭代优化观测成功率(剔除本身不够分配时间的样本): {}'.format(
            METHOD, success_rate[1]))

        print('方法{}，未迭代优化climb状态观测成功率(包含本身不够分配时间的样本): {}'.format(
            METHOD, success_rate[2]))
        print('方法{}，未迭代优化operation状态观测成功率(剔除本身不够分配时间的样本): {}'.format(
            METHOD, success_rate[3]))

    # 验算
    end_time = time.time()
    allocation_time = end_time - start_time
    print("分配算法的运行时间：{} 秒".format(allocation_time))
    check_crossover_overflow(
        list_cm_avail, ground_station_cm_use_plan, arr_all_start_time, arr_all_end_time)

    # ==================== 新增模拟退火优化代码块====================
    if USE_SA == 'TRUE':
        print("\n" + "=" * 70)
        print("第二阶段：模拟退火优化")
        print("=" * 70)
        print("正在使用模拟退火算法优化负载均衡...")

        # 执行SA优化
        ground_station_cm_use_plan = optimize_with_sa(
            all_data=all_data,
            dict_sat_laps_sta_time_all=dict_sat_laps_sta_time_all,
            keys_line=keys_line,
            arr_all_start_time=arr_all_start_time,
            arr_all_end_time=arr_all_end_time,
            list_cm_avail=list_cm_avail,
            initial_plan=ground_station_cm_use_plan,
            satellite_ground_station=satellite_ground_station,
            num_stations=num_stations,
            max_time=SA_MAX_TIME,
            verbose=True
        )

        # SA优化后重新计算成功率
        print("\n" + "=" * 70)
        print("SA优化后结果统计")
        print("=" * 70)

        # 重建ground_station_cm_use_plan_sort_by_start_time用于计算成功率
        # 按照开始时间排序ground_station_cm_use_plan
        start_times = ground_station_cm_use_plan[:, 2].copy()
        sort_indices = np.argsort(start_times)
        ground_station_cm_use_plan_sort_by_start_time = ground_station_cm_use_plan[sort_indices]

        success_rate_sa = cal_success_rate(
            ground_station_cm_use_plan_sort_by_start_time, dict_sat_laps_sta_time_all)

        if OPTIMIZATION == 'TRUE':
            print('方法{}，SA优化后观测成功率(包含本身不够分配时间的样本): {}'.format(
                METHOD, success_rate_sa[0]))
            print('方法{}，SA优化后观测成功率(剔除本身不够分配时间的样本): {}'.format(
                METHOD, success_rate_sa[1]))
            print('方法{}，SA优化后climb状态观测成功率(包含本身不够分配时间的样本): {}'.format(
                METHOD, success_rate_sa[2]))
            print('方法{}，SA优化后operation状态观测成功率(剔除本身不够分配时间的样本): {}'.format(
                METHOD, success_rate_sa[3]))

        # SA优化后验算
        print("\nSA优化后验算：")
        check_crossover_overflow(
            list_cm_avail, ground_station_cm_use_plan, arr_all_start_time, arr_all_end_time)
    # ==================== 新增模拟退火优化代码块（结束）====================

    # # 答案格式转化
    if ANSWER_TYPE == 'TRUE':
        start_time1 = time.time()
        print('输出格式转换中……')
        answer_for_excel = answer_type_transform(
            keys_line, ground_station_cm_use_plan, all_data)

        # 检查并创建output目录（如果不存在）
        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 获取当前时间并格式化为时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 文件名带上时间戳后缀
        file_name = f'{output_dir}/answer_output_QV_only_{timestamp}.xlsx'

        # 使用ExcelWriter上下文管理器写入Excel文件
        with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
            for i, array in enumerate(answer_for_excel):
                df = pd.DataFrame(array)
                sheet_name = 'Sheet' + str(i + 1)
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        print("数据已成功写入Excel的不同工作表")
        end_time1 = time.time()
        allocation_time1 = end_time1 - start_time1
        print("答案存入文件的运行时间：{} 秒".format(allocation_time1))
        print("分配算法+答案存入文件的运行时间：{} 秒".format(allocation_time + allocation_time1))

    validate_allocation_results(all_data, ground_station_cm_use_plan, keys_line)


if __name__ == '__main__':
    main()