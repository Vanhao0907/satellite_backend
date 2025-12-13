"""
卫星测控任务分配结果验证模块

本模块用于验证算法分配结果是否满足以下需求：
1. 可见弧段任务最小时长限制（≥300s）
2. 任务间隔约束时间（同一天线≥300s）

使用方法：
在main.py执行完成后调用validate_allocation_results()函数
"""

import numpy as np
import pandas as pd
from collections import defaultdict
from datetime import datetime
import os


def validate_requirement1(all_data, ground_station_cm_use_plan, keys_line):
    """
    验证需求1: 可见弧段任务最小时长限制（≥300s）

    参数：
    all_data - 原始数据列表（来自main.py）
    ground_station_cm_use_plan - 分配方案数组（来自main.py）
    keys_line - 圈次键列表（来自main.py）

    返回：
    验证结果字典
    """
    print("\n" + "=" * 70)
    print("【需求1验证】可见弧段任务最小时长限制（≥300秒）")
    print("=" * 70)

    # 构建分配索引：(站点, 天线, 卫星, 圈次, 状态) -> 是否分配
    allocation_index = {}
    for idx, alloc in enumerate(ground_station_cm_use_plan):
        if alloc[0] < 1e9:  # 有效分配
            sat, laps, status = keys_line[idx].split('-')
            key = (int(alloc[0]), int(alloc[1]), sat, int(laps), status)
            allocation_index[key] = True

    # 遍历原始数据，检查时长不足的记录
    total_records = 0
    duration_insufficient = 0
    correctly_rejected = 0
    anomalies = []

    for station_idx, folder_data in enumerate(all_data, start=1):
        folder_name = list(folder_data.keys())[0]
        data_list = folder_data[folder_name]

        for antenna_idx, df in enumerate(data_list, start=1):
            # 处理列名
            start_col = next((col for col in ['start(UTC)', 'start'] if col in df.columns), None)
            stop_col = next((col for col in ['stop(UTC)', 'stop'] if col in df.columns), None)

            if start_col is None or stop_col is None:
                continue

            # 计算时长
            start_times = pd.to_datetime(df[start_col]).astype('int64') // 10 ** 9
            stop_times = pd.to_datetime(df[stop_col]).astype('int64') // 10 ** 9
            durations = stop_times - start_times

            # 获取卫星、圈次、状态信息
            sat_col = 'sat' if 'sat' in df.columns else 'Sat'
            laps_col = 'laps' if 'laps' in df.columns else 'Laps'
            status_col = 'Status' if 'Status' in df.columns else 'status'

            for row_idx in range(len(df)):
                total_records += 1
                duration = durations.iloc[row_idx]

                if duration < 300:
                    duration_insufficient += 1

                    # 检查是否被分配
                    sat = str(df.iloc[row_idx][sat_col])
                    laps = int(df.iloc[row_idx][laps_col])
                    status = str(df.iloc[row_idx][status_col])

                    key = (station_idx, antenna_idx, sat, laps, status)

                    if key in allocation_index:
                        # 异常：时长不足但被分配
                        anomalies.append({
                            '站点': folder_name,
                            '天线': antenna_idx,
                            '卫星-圈次-状态': f"{sat}-{laps}-{status}",
                            '可见时长(秒)': int(duration),
                            '开始时间': datetime.fromtimestamp(start_times.iloc[row_idx]).strftime('%Y-%m-%d %H:%M:%S'),
                            '结束时间': datetime.fromtimestamp(stop_times.iloc[row_idx]).strftime('%Y-%m-%d %H:%M:%S'),
                            '问题': '时长不足但仍被分配'
                        })
                    else:
                        correctly_rejected += 1

    # 生成结果
    results = {
        'total_records': total_records,
        'duration_insufficient': duration_insufficient,
        'correctly_rejected': correctly_rejected,
        'anomaly_count': len(anomalies),
        'anomalies': anomalies,
        'pass_rate': correctly_rejected / duration_insufficient * 100 if duration_insufficient > 0 else 100
    }

    # 打印结果
    print(f"\n总弧段记录数：{total_records:,} 条")
    print(f"可见时长不足(<300s)：{duration_insufficient:,} 条 ({duration_insufficient / total_records * 100:.1f}%)")
    print(f"正确拒绝数量：{correctly_rejected:,} 条")

    if len(anomalies) == 0:
        print(f"✓ 异常数量：0 条")
        print("\n【验证结论】✓ 完全通过：所有时长不足的弧段都被正确拒绝")
    else:
        print(f"✗ 异常数量：{len(anomalies):,} 条 ({len(anomalies) / duration_insufficient * 100:.1f}%)")
        print(f"\n【验证结论】通过率：{results['pass_rate']:.2f}%")
        print(f"发现问题：{len(anomalies)}条时长不足的弧段仍被分配了资源")

        print("\n【异常详情】（显示前10条）：")
        for i, anomaly in enumerate(anomalies[:10], 1):
            print(f"\n{i}. {anomaly['站点']}-天线{anomaly['天线']:02d}")
            print(f"   {anomaly['卫星-圈次-状态']}")
            print(f"   可见时长：{anomaly['可见时长(秒)']}秒 < 300秒")
            print(f"   时间：{anomaly['开始时间']} ~ {anomaly['结束时间']}")

        if len(anomalies) > 10:
            print(f"\n   ... 还有 {len(anomalies) - 10} 条异常未显示")

    return results


def validate_requirement2(ground_station_cm_use_plan, keys_line, all_data):
    """
    验证需求2: 任务间隔约束时间（同一天线≥300s）

    参数：
    ground_station_cm_use_plan - 分配方案数组（来自main.py）
    keys_line - 圈次键列表（来自main.py）
    all_data - 原始数据列表（用于获取站点名称）

    返回：
    验证结果字典
    """
    print("\n" + "=" * 70)
    print("【需求2验证】同一天线任务间隔约束（≥300秒）")
    print("=" * 70)

    # 构建站点名称映射
    station_names = []
    for folder_data in all_data:
        station_names.append(list(folder_data.keys())[0])

    # 提取所有成功分配的任务
    successful_tasks = []
    for idx, alloc in enumerate(ground_station_cm_use_plan):
        if alloc[0] < 100 and alloc[2] < 1e10:  # 有效分配
            sat, laps, status = keys_line[idx].split('-')
            successful_tasks.append({
                'station': int(alloc[0]),
                'antenna': int(alloc[1]),
                'sat_laps': f"{sat}-{laps}",
                'start_time': int(alloc[2]),
                'end_time': int(alloc[3])
            })

    print(f"成功分配的任务数：{len(successful_tasks)} 个")

    # 按（站点, 天线）分组
    antenna_tasks = defaultdict(list)
    for task in successful_tasks:
        key = (task['station'], task['antenna'])
        antenna_tasks[key].append(task)

    print(f"涉及的天线数：{len(antenna_tasks)} 根")

    # 对每根天线的任务按开始时间排序
    for key in antenna_tasks:
        antenna_tasks[key].sort(key=lambda x: x['start_time'])

    # 检查间隔
    conflicts = []
    overlaps = []
    total_pairs = 0
    valid_pairs = 0

    for (station, antenna), tasks in antenna_tasks.items():
        if len(tasks) < 2:
            continue

        station_name = station_names[station - 1] if station <= len(station_names) else f"站点{station}"

        for i in range(len(tasks) - 1):
            total_pairs += 1
            prev_task = tasks[i]
            next_task = tasks[i + 1]

            interval = next_task['start_time'] - prev_task['end_time']

            if interval < 0:
                # 时间重叠
                overlaps.append({
                    '站点': station_name,
                    '天线': antenna,
                    '前任务': prev_task['sat_laps'],
                    '前任务结束时间': datetime.fromtimestamp(prev_task['end_time']).strftime('%Y-%m-%d %H:%M:%S'),
                    '后任务': next_task['sat_laps'],
                    '后任务开始时间': datetime.fromtimestamp(next_task['start_time']).strftime('%Y-%m-%d %H:%M:%S'),
                    '重叠时长(秒)': abs(interval)
                })
            elif interval < 300:
                # 间隔不足
                conflicts.append({
                    '站点': station_name,
                    '天线': antenna,
                    '前任务': prev_task['sat_laps'],
                    '前任务结束时间': datetime.fromtimestamp(prev_task['end_time']).strftime('%Y-%m-%d %H:%M:%S'),
                    '后任务': next_task['sat_laps'],
                    '后任务开始时间': datetime.fromtimestamp(next_task['start_time']).strftime('%Y-%m-%d %H:%M:%S'),
                    '实际间隔(秒)': interval,
                    '缺少间隔(秒)': 300 - interval
                })
            else:
                valid_pairs += 1

    # 生成结果
    results = {
        'checked_antennas': len(antenna_tasks),
        'total_task_pairs': total_pairs,
        'valid_pairs': valid_pairs,
        'conflict_count': len(conflicts),
        'overlap_count': len(overlaps),
        'conflicts': conflicts,
        'overlaps': overlaps,
        'pass_rate': valid_pairs / total_pairs * 100 if total_pairs > 0 else 100
    }

    # 打印结果
    print(f"\n检查的任务对数：{total_pairs:,} 对")
    print(f"符合约束的任务对：{valid_pairs:,} 对 ({results['pass_rate']:.1f}%)")

    if len(overlaps) > 0:
        print(f"✗✗ 时间重叠：{len(overlaps):,} 对（严重问题！）")
    else:
        print(f"✓ 时间重叠：0 对")

    if len(conflicts) > 0:
        print(f"✗ 间隔不足：{len(conflicts):,} 对")
    else:
        print(f"✓ 间隔不足：0 对")

    # 打印详情
    if len(overlaps) > 0:
        print("\n【严重问题：时间重叠详情】（显示前5条）：")
        for i, overlap in enumerate(overlaps[:5], 1):
            print(f"\n{i}. {overlap['站点']}-天线{overlap['天线']:02d}")
            print(f"   前任务：{overlap['前任务']} (结束: {overlap['前任务结束时间']})")
            print(f"   后任务：{overlap['后任务']} (开始: {overlap['后任务开始时间']})")
            print(f"   ✗✗ 时间重叠：{overlap['重叠时长(秒)']}秒")

        if len(overlaps) > 5:
            print(f"\n   ... 还有 {len(overlaps) - 5} 处重叠未显示")

    if len(conflicts) > 0:
        print("\n【间隔不足详情】（显示前10条）：")
        for i, conflict in enumerate(conflicts[:10], 1):
            print(f"\n{i}. {conflict['站点']}-天线{conflict['天线']:02d}")
            print(f"   前任务：{conflict['前任务']} (结束: {conflict['前任务结束时间']})")
            print(f"   后任务：{conflict['后任务']} (开始: {conflict['后任务开始时间']})")
            print(f"   ✗ 实际间隔：{conflict['实际间隔(秒)']}秒 < 300秒（缺少{conflict['缺少间隔(秒)']}秒）")

        if len(conflicts) > 10:
            print(f"\n   ... 还有 {len(conflicts) - 10} 处冲突未显示")

    # 验证结论
    print("\n【验证结论】")
    if len(overlaps) == 0 and len(conflicts) == 0:
        print("✓ 完全通过：所有任务间隔都符合300秒约束")
    else:
        if len(overlaps) > 0:
            print(f"✗✗ 严重问题：发现{len(overlaps)}处时间重叠")
        if len(conflicts) > 0:
            print(f"✗ 发现问题：{len(conflicts)}处间隔不足的情况")
        print(f"通过率：{results['pass_rate']:.2f}%")

    return results


def export_validation_report(req1_results, req2_results, output_dir='./validation_reports'):
    """
    导出验证报告到Excel

    参数：
    req1_results - 需求1验证结果
    req2_results - 需求2验证结果
    output_dir - 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    print("\n" + "=" * 70)
    print("正在导出验证报告...")
    print("=" * 70)

    # 导出需求1异常详情
    if req1_results and req1_results['anomalies']:
        df = pd.DataFrame(req1_results['anomalies'])
        excel_file = os.path.join(output_dir, f'需求1_时长不足异常_{timestamp}.xlsx')
        df.to_excel(excel_file, index=False, engine='openpyxl')
        print(f"✓ 需求1异常详情已导出: {excel_file}")

    # 导出需求2冲突详情
    if req2_results:
        if req2_results['conflicts']:
            df = pd.DataFrame(req2_results['conflicts'])
            excel_file = os.path.join(output_dir, f'需求2_间隔不足冲突_{timestamp}.xlsx')
            df.to_excel(excel_file, index=False, engine='openpyxl')
            print(f"✓ 需求2间隔不足详情已导出: {excel_file}")

        if req2_results['overlaps']:
            df = pd.DataFrame(req2_results['overlaps'])
            excel_file = os.path.join(output_dir, f'需求2_时间重叠_{timestamp}.xlsx')
            df.to_excel(excel_file, index=False, engine='openpyxl')
            print(f"✓ 需求2时间重叠详情已导出: {excel_file}")

    # 导出汇总报告
    summary_file = os.path.join(output_dir, f'验证汇总报告_{timestamp}.txt')
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("卫星测控任务分配结果验证报告\n")
        f.write("=" * 70 + "\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        if req1_results:
            f.write("【需求1：可见弧段最小时长限制（≥300秒）】\n")
            f.write(f"总记录数: {req1_results['total_records']:,}\n")
            f.write(f"时长不足记录数: {req1_results['duration_insufficient']:,}\n")
            f.write(f"正确拒绝数: {req1_results['correctly_rejected']:,}\n")
            f.write(f"异常数: {req1_results['anomaly_count']:,}\n")
            f.write(f"通过率: {req1_results['pass_rate']:.2f}%\n\n")

        if req2_results:
            f.write("【需求2：同一天线任务间隔约束（≥300秒）】\n")
            f.write(f"检查天线数: {req2_results['checked_antennas']:,}\n")
            f.write(f"检查任务对数: {req2_results['total_task_pairs']:,}\n")
            f.write(f"间隔不足冲突数: {req2_results['conflict_count']:,}\n")
            f.write(f"时间重叠数: {req2_results['overlap_count']:,}\n")
            f.write(f"通过率: {req2_results['pass_rate']:.2f}%\n")

    print(f"✓ 验证汇总报告已导出: {summary_file}")
    print("=" * 70)


def validate_allocation_results(all_data, ground_station_cm_use_plan, keys_line):
    """
    验证分配结果的主函数

    参数：
    all_data - 原始数据列表（来自main.py）
    ground_station_cm_use_plan - 分配方案数组（来自main.py）
    keys_line - 圈次键列表（来自main.py）

    使用示例：
    在main.py的最后添加：
    from validate_results import validate_allocation_results
    validate_allocation_results(all_data, ground_station_cm_use_plan, keys_line)
    """
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "开始验证分配结果" + " " * 20 + "║")
    print("╚" + "═" * 68 + "╝")

    # 验证需求1
    req1_results = validate_requirement1(all_data, ground_station_cm_use_plan, keys_line)

    # 验证需求2
    req2_results = validate_requirement2(ground_station_cm_use_plan, keys_line, all_data)

    # 导出报告
    export_validation_report(req1_results, req2_results)

    # 总结
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 24 + "验证完成" + " " * 24 + "║")
    print("╚" + "═" * 68 + "╝")

    print("\n【总体结论】")
    if req1_results['anomaly_count'] == 0 and req2_results['conflict_count'] == 0 and req2_results[
        'overlap_count'] == 0:
        print("✓✓✓ 完全通过：所有约束条件均满足！")
    else:
        issues = []
        if req1_results['anomaly_count'] > 0:
            issues.append(f"需求1: {req1_results['anomaly_count']}个时长不足异常")
        if req2_results['overlap_count'] > 0:
            issues.append(f"需求2: {req2_results['overlap_count']}个时间重叠（严重）")
        if req2_results['conflict_count'] > 0:
            issues.append(f"需求2: {req2_results['conflict_count']}个间隔不足")

        print(f"⚠ 发现问题：{', '.join(issues)}")
        print("\n详细报告已保存到 ./validation_reports/ 目录")

    print("=" * 70 + "\n")

    return req1_results, req2_results