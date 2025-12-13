"""
模拟退火优化模块 v2.2 - 优先级2改进版（分阶段优化）
改进要点：
1. 保留优先级1的所有改进
2. 新增分阶段优化策略：
   - 第一阶段：激进均衡（只关注负载均衡）
   - 第二阶段：微调优化（均衡+成功率）
"""

import numpy as np
import copy
from collections import defaultdict
import time


class SimulatedAnnealing:
    """模拟退火优化器 - 优先级2改进版（分阶段优化）"""

    def __init__(self, all_data, dict_sat_laps_sta_time_all, keys_line,
                 arr_all_start_time, arr_all_end_time, list_cm_avail,
                 initial_plan, satellite_ground_station, num_stations):
        """
        初始化SA优化器

        参数：
        all_data - 原始数据
        dict_sat_laps_sta_time_all - 卫星圈次可观测时间字典
        keys_line - 圈次键列表
        arr_all_start_time - 各地面站观测开始时间
        arr_all_end_time - 各地面站观测结束时间
        list_cm_avail - 各地面站天线数量
        initial_plan - 初始贪心分配方案
        satellite_ground_station - 各圈次可观测的地面站列表
        num_stations - 地面站数量
        """
        self.all_data = all_data
        self.dict_sat_laps_sta_time_all = dict_sat_laps_sta_time_all
        self.keys_line = keys_line
        self.arr_all_start_time = arr_all_start_time
        self.arr_all_end_time = arr_all_end_time
        self.list_cm_avail = list_cm_avail
        self.satellite_ground_station = satellite_ground_station
        self.num_stations = num_stations

        # 初始方案（深拷贝避免修改原数据）
        self.current_plan = copy.deepcopy(initial_plan)
        self.best_plan = copy.deepcopy(initial_plan)

        # SA参数（会在optimize方法中根据阶段动态设置）
        self.T = 5000.0
        self.T_min = 0.01
        self.alpha = 0.92
        self.inner_iterations = 1000

        # ========== 【改进2-5】分阶段优化参数 ==========
        self.current_phase = 1  # 当前阶段：1=激进均衡，2=微调优化
        # ========== 【改进2-5结束】 ==========

        # 统计信息
        self.iteration_count = 0
        self.accepted_count = 0
        self.improved_count = 0

    # ========== 【改进2-5】新增阶段专用目标函数 ==========
    def calculate_objective(self, plan, phase=2):
        """
        计算目标函数值

        参数：
        plan - 分配方案
        phase - 优化阶段（1=激进均衡，2=微调优化）

        返回：(总分, 成功率, 负载标准差, 负载差距, 惩罚项)
        """
        # 1. 成功率计算
        valid_tasks = 0
        total_tasks = len(self.keys_line)

        for i in range(len(plan)):
            if plan[i][0] < 100 and plan[i][2] < 1e10:  # 有效分配
                valid_tasks += 1

        success_rate = valid_tasks / total_tasks if total_tasks > 0 else 0

        # 2. 负载均衡计算（时间占用率）
        station_usage = np.zeros(self.num_stations)
        station_total_time = np.zeros(self.num_stations)

        # 计算每个站的总可用时间窗口
        for i in range(self.num_stations):
            non_zero_times = self.arr_all_end_time[i][self.arr_all_end_time[i] > 0]
            if len(non_zero_times) > 0:
                station_total_time[i] = non_zero_times.sum()

        # 计算每个站的实际占用时间
        for i in range(len(plan)):
            if plan[i][0] < 100 and plan[i][2] < 1e10:
                station_idx = int(plan[i][0]) - 1
                duration = plan[i][3] - plan[i][2]
                station_usage[station_idx] += duration

        # 计算利用率
        utilization = np.zeros(self.num_stations)
        for i in range(self.num_stations):
            if station_total_time[i] > 0:
                utilization[i] = station_usage[i] / station_total_time[i]

        # 负载标准差（越小越好）
        load_std = np.std(utilization)

        # 计算最大负载和最小负载的差距
        valid_utilization = utilization[station_total_time > 0]
        if len(valid_utilization) > 0:
            load_gap = np.max(valid_utilization) - np.min(valid_utilization)
        else:
            load_gap = 0

        # 3. 约束违反惩罚
        penalty = self._calculate_penalty(plan)

        # 4. 根据阶段计算目标函数
        if phase == 1:  # 第一阶段：激进均衡（不考虑成功率）
            # 只关注负载均衡，不考虑成功率
            # 允许成功率轻微下降以换取更好的均衡性
            total_score = -1000 * load_std - 500 * load_gap - penalty
        else:  # 第二阶段：微调优化（均衡+成功率）
            # 兼顾成功率和负载均衡
            total_score = 100 * success_rate - 100 * load_std - 150 * load_gap - penalty
        # ========== 【改进2-5结束】 ==========

        return total_score, success_rate, load_std, load_gap, penalty

    def _calculate_penalty(self, plan):
        """计算约束违反惩罚"""
        penalty = 0

        # 按天线组织任务
        antenna_tasks = defaultdict(list)
        for i, alloc in enumerate(plan):
            if alloc[0] < 100 and alloc[2] < 1e10:  # 有效分配
                key = (int(alloc[0]), int(alloc[1]))  # (站点, 天线)
                antenna_tasks[key].append({
                    'index': i,
                    'start': alloc[2],
                    'end': alloc[3],
                    'sat_laps': self.keys_line[i]
                })

        # 检查每根天线的任务
        for (station, antenna), tasks in antenna_tasks.items():
            # 按开始时间排序
            tasks.sort(key=lambda x: x['start'])

            # 检查任务时长
            for task in tasks:
                duration = task['end'] - task['start']
                if duration < 300:
                    penalty += 1000  # 严重违反

            # 检查相邻任务间隔
            for i in range(len(tasks) - 1):
                interval = tasks[i + 1]['start'] - tasks[i]['end']

                # 判断是否同一卫星
                sat1 = tasks[i]['sat_laps'][:5]
                sat2 = tasks[i + 1]['sat_laps'][:5]

                if sat1 == sat2:  # 同一卫星
                    if interval < 300:
                        penalty += 500
                else:  # 不同卫星
                    if interval < 600:
                        penalty += 500

                # 时间重叠
                if interval < 0:
                    penalty += 2000  # 最严重违反

        return penalty

    def _get_task_candidates(self, task_index):
        """
        获取某个任务可以分配的候选天线列表

        返回：[(station_idx, antenna_idx, start_time, end_time), ...]
        """
        candidates = []
        sat_laps_key = self.keys_line[task_index]

        # 获取该任务的可观测地面站
        observable_stations = self.satellite_ground_station[task_index]

        for station_idx in observable_stations:
            # 获取该站的开始和结束时间
            start_time = self.arr_all_start_time[station_idx, task_index]
            end_time = self.arr_all_end_time[station_idx, task_index]

            if start_time < 1e10 and end_time > 0:  # 有效时间窗口
                # 检查时长是否满足300s
                if end_time - start_time >= 300:
                    # 该站的所有天线都是候选
                    for antenna_idx in range(self.list_cm_avail[station_idx]):
                        candidates.append((
                            station_idx,
                            antenna_idx,
                            start_time,
                            end_time
                        ))

        return candidates

    def _can_allocate(self, plan, task_index, station_idx, antenna_idx, start_time, end_time):
        """
        检查是否可以将任务分配到指定天线

        返回：True/False
        """
        # 检查时长
        if end_time - start_time < 300:
            return False

        # 获取该天线的所有已分配任务
        antenna_key = (station_idx + 1, antenna_idx + 1)
        existing_tasks = []

        for i, alloc in enumerate(plan):
            if i != task_index and alloc[0] == antenna_key[0] and alloc[1] == antenna_key[1]:
                if alloc[2] < 1e10:  # 有效分配
                    existing_tasks.append({
                        'index': i,
                        'start': alloc[2],
                        'end': alloc[3],
                        'sat_laps': self.keys_line[i]
                    })

        # 按时间排序
        existing_tasks.sort(key=lambda x: x['start'])

        # 检查与现有任务的时间冲突
        current_sat = self.keys_line[task_index][:5]

        for task in existing_tasks:
            task_sat = task['sat_laps'][:5]

            # 检查时间重叠
            if not (end_time <= task['start'] or start_time >= task['end']):
                return False

            # 检查间隔约束
            if end_time <= task['start']:  # 新任务在前
                interval = task['start'] - end_time
                min_interval = 300 if current_sat == task_sat else 600
                if interval < min_interval:
                    return False
            else:  # 新任务在后
                interval = start_time - task['end']
                min_interval = 300 if current_sat == task_sat else 600
                if interval < min_interval:
                    return False

        return True

    def _neighbor_targeted_reallocation(self, plan):
        """
        邻域操作：定向任务迁移
        强制从高负载天线迁移任务到低负载天线
        """
        new_plan = copy.deepcopy(plan)

        # 计算各站点负载
        station_usage = np.zeros(self.num_stations)
        station_total_time = np.zeros(self.num_stations)

        # 计算总可用时间
        for i in range(self.num_stations):
            non_zero_times = self.arr_all_end_time[i][self.arr_all_end_time[i] > 0]
            if len(non_zero_times) > 0:
                station_total_time[i] = non_zero_times.sum()

        # 计算实际占用时间
        for alloc in plan:
            if alloc[0] < 100 and alloc[2] < 1e10:
                station_idx = int(alloc[0]) - 1
                station_usage[station_idx] += (alloc[3] - alloc[2])

        # 计算利用率
        utilization = np.zeros(self.num_stations)
        for i in range(self.num_stations):
            if station_total_time[i] > 0:
                utilization[i] = station_usage[i] / station_total_time[i]
            else:
                utilization[i] = 0

        # 找到负载最高的前3个站点和负载最低的前5个站点
        valid_stations = [i for i in range(self.num_stations) if station_total_time[i] > 0]

        if len(valid_stations) < 2:
            return new_plan, False

        # 按利用率排序
        sorted_by_load = sorted(valid_stations, key=lambda x: utilization[x])

        # 最低负载的前5个站点
        low_load_stations = sorted_by_load[:min(5, len(sorted_by_load))]
        # 最高负载的前3个站点
        high_load_stations = sorted_by_load[-min(3, len(sorted_by_load)):]

        # 增加尝试次数
        max_attempts = 50
        attempts = 0

        while attempts < max_attempts:
            attempts += 1

            # 随机选择一个高负载站点
            high_station = np.random.choice(high_load_stations)

            # 找到该站点的所有任务
            station_tasks = []
            for i, alloc in enumerate(plan):
                if alloc[0] == high_station + 1 and alloc[2] < 1e10:
                    station_tasks.append(i)

            if len(station_tasks) == 0:
                continue

            # 随机选择一个任务
            task_idx = np.random.choice(station_tasks)

            # 获取该任务的候选天线
            candidates = self._get_task_candidates(task_idx)

            # 只考虑低负载站点的候选
            low_load_candidates = [
                c for c in candidates
                if c[0] in low_load_stations
            ]

            if len(low_load_candidates) == 0:
                continue

            # 优先选择负载最低的候选
            low_load_candidates_sorted = sorted(
                low_load_candidates,
                key=lambda c: utilization[c[0]]
            )

            # 尝试前3个最低负载的候选
            for candidate in low_load_candidates_sorted[:3]:
                new_station, new_antenna, new_start, new_end = candidate

                # 检查是否可以分配
                if self._can_allocate(new_plan, task_idx, new_station, new_antenna, new_start, new_end):
                    # 更新分配方案
                    new_plan[task_idx] = np.array([
                        new_station + 1,
                        new_antenna + 1,
                        new_start,
                        new_end,
                        plan[task_idx][4]  # 保持状态标志
                    ])
                    return new_plan, True

        return new_plan, False

    def _neighbor_task_reallocation(self, plan):
        """
        邻域操作1：任务迁移
        从高负载天线迁移任务到低负载天线
        """
        new_plan = copy.deepcopy(plan)

        # 计算各站点负载
        station_load = np.zeros(self.num_stations)
        for alloc in plan:
            if alloc[0] < 100 and alloc[2] < 1e10:
                station_idx = int(alloc[0]) - 1
                station_load[station_idx] += (alloc[3] - alloc[2])

        # 找到高负载和低负载的站点
        high_load_stations = np.where(station_load > np.median(station_load))[0]
        low_load_stations = np.where(station_load < np.median(station_load))[0]

        if len(high_load_stations) == 0 or len(low_load_stations) == 0:
            return new_plan, False

        # 随机选择一个高负载站点的任务
        attempts = 0
        max_attempts = 50

        while attempts < max_attempts:
            attempts += 1

            high_station = np.random.choice(high_load_stations)

            # 找到该站点的任务
            station_tasks = []
            for i, alloc in enumerate(plan):
                if alloc[0] == high_station + 1 and alloc[2] < 1e10:
                    station_tasks.append(i)

            if len(station_tasks) == 0:
                continue

            # 随机选择一个任务
            task_idx = np.random.choice(station_tasks)

            # 获取该任务的候选天线
            candidates = self._get_task_candidates(task_idx)

            # 只考虑低负载站点的候选
            low_load_candidates = [
                c for c in candidates
                if c[0] in low_load_stations
            ]

            if len(low_load_candidates) == 0:
                continue

            # 随机选择一个候选
            new_station, new_antenna, new_start, new_end = \
                low_load_candidates[np.random.randint(len(low_load_candidates))]

            # 检查是否可以分配
            if self._can_allocate(new_plan, task_idx, new_station, new_antenna, new_start, new_end):
                # 更新分配方案
                new_plan[task_idx] = np.array([
                    new_station + 1,
                    new_antenna + 1,
                    new_start,
                    new_end,
                    plan[task_idx][4]  # 保持状态标志
                ])
                return new_plan, True

        return new_plan, False

    def _neighbor_task_swap(self, plan):
        """
        邻域操作2：任务交换
        交换两个任务的分配
        """
        new_plan = copy.deepcopy(plan)

        # 找到所有有效任务
        valid_tasks = []
        for i, alloc in enumerate(plan):
            if alloc[0] < 100 and alloc[2] < 1e10:
                valid_tasks.append(i)

        if len(valid_tasks) < 2:
            return new_plan, False

        # 随机选择两个任务
        attempts = 0
        max_attempts = 50

        while attempts < max_attempts:
            attempts += 1

            task1_idx, task2_idx = np.random.choice(valid_tasks, 2, replace=False)

            # 获取两个任务的候选天线
            candidates1 = self._get_task_candidates(task1_idx)
            candidates2 = self._get_task_candidates(task2_idx)

            # 检查task1是否可以分配到task2的位置
            station2 = int(plan[task2_idx][0]) - 1
            antenna2 = int(plan[task2_idx][1]) - 1

            # 检查task2是否可以分配到task1的位置
            station1 = int(plan[task1_idx][0]) - 1
            antenna1 = int(plan[task1_idx][1]) - 1

            # 查找对应的时间窗口
            valid_swap = False
            for c1 in candidates1:
                if c1[0] == station2 and c1[1] == antenna2:
                    for c2 in candidates2:
                        if c2[0] == station1 and c2[1] == antenna1:
                            # 暂时移除两个任务
                            temp_plan = copy.deepcopy(plan)
                            temp_plan[task1_idx] = np.ones(5) * 1e10
                            temp_plan[task2_idx] = np.ones(5) * 1e10

                            # 检查交换后是否合法
                            if (self._can_allocate(temp_plan, task1_idx, station2, antenna2, c1[2], c1[3]) and
                                    self._can_allocate(temp_plan, task2_idx, station1, antenna1, c2[2], c2[3])):
                                # 执行交换
                                new_plan[task1_idx] = np.array([
                                    station2 + 1, antenna2 + 1, c1[2], c1[3], plan[task1_idx][4]
                                ])
                                new_plan[task2_idx] = np.array([
                                    station1 + 1, antenna1 + 1, c2[2], c2[3], plan[task2_idx][4]
                                ])
                                valid_swap = True
                                break
                    if valid_swap:
                        break

            if valid_swap:
                return new_plan, True

        return new_plan, False

    def _generate_neighbor(self, plan):
        """
        生成邻域解

        返回：(新方案, 是否成功)
        """
        rand = np.random.random()

        if rand < 0.5:  # 50%概率：定向迁移
            return self._neighbor_targeted_reallocation(plan)
        elif rand < 0.8:  # 30%概率：随机迁移
            return self._neighbor_task_reallocation(plan)
        else:  # 20%概率：任务交换
            return self._neighbor_task_swap(plan)

    # ========== 【改进2-5】新增单阶段优化方法 ==========
    def _optimize_single_phase(self, phase, max_time, verbose=True):
        """
        单阶段优化

        参数：
        phase - 阶段编号（1=激进均衡，2=微调优化）
        max_time - 最大运行时间
        verbose - 是否打印详细信息

        返回：(优化后的方案, 是否成功)
        """
        start_time = time.time()
        self.current_phase = phase

        # 根据阶段设置参数
        if phase == 1:
            # 第一阶段：激进均衡
            self.T = 10000.0  # 超高初始温度
            self.alpha = 0.90  # 超慢冷却
            self.inner_iterations = 2000  # 更多迭代
            phase_name = "激进均衡"
        else:
            # 第二阶段：微调优化
            self.T = 2000.0  # 正常温度
            self.alpha = 0.93  # 正常冷却
            self.inner_iterations = 1000  # 正常迭代
            phase_name = "微调优化"

        if verbose:
            print(f"\n{'=' * 70}")
            print(f"第{phase}阶段：{phase_name}")
            print(f"{'=' * 70}")
            print(f"参数设置：T0={self.T}, alpha={self.alpha}, L={self.inner_iterations}")

        # 计算初始目标函数值
        current_score, current_success, current_std, current_gap, current_penalty = \
            self.calculate_objective(self.current_plan, phase=phase)
        best_score = current_score

        if verbose:
            print(f"初始解：成功率={current_success:.4f}, 负载标准差={current_std:.4f}, "
                  f"负载差距={current_gap:.4f}, 惩罚={current_penalty:.0f}")
            print(f"初始目标函数值：{current_score:.2f}")
            print("-" * 70)

        temperature_count = 0
        phase_iteration_count = 0
        phase_accepted_count = 0
        phase_improved_count = 0

        # 主循环
        while self.T > self.T_min:
            temperature_count += 1

            # 检查时间限制
            if time.time() - start_time > max_time:
                if verbose:
                    print(f"\n达到阶段时间限制 {max_time}秒")
                break

            # 内循环
            accepted_in_temp = 0
            improved_in_temp = 0

            for _ in range(self.inner_iterations):
                self.iteration_count += 1
                phase_iteration_count += 1

                # 生成邻域解
                new_plan, success = self._generate_neighbor(self.current_plan)

                if not success:
                    continue

                # 计算新解的目标函数值
                new_score, new_success, new_std, new_gap, new_penalty = \
                    self.calculate_objective(new_plan, phase=phase)

                # 计算差值
                delta = new_score - current_score

                # Metropolis接受准则
                if delta > 0:  # 更好的解，直接接受
                    self.current_plan = new_plan
                    current_score = new_score
                    current_success = new_success
                    current_std = new_std
                    current_gap = new_gap
                    current_penalty = new_penalty

                    self.accepted_count += 1
                    phase_accepted_count += 1
                    accepted_in_temp += 1
                    improved_in_temp += 1
                    self.improved_count += 1
                    phase_improved_count += 1

                    # 更新最优解
                    if new_score > best_score:
                        self.best_plan = copy.deepcopy(new_plan)
                        best_score = new_score

                        if verbose and phase_iteration_count % 200 == 0:
                            print(f"[阶段{phase}-迭代{phase_iteration_count}] 发现更优解！"
                                  f"成功率={new_success:.4f}, "
                                  f"负载标准差={new_std:.4f}, "
                                  f"负载差距={new_gap:.4f}, "
                                  f"得分={new_score:.2f}")

                else:  # 较差的解，以一定概率接受
                    accept_prob = np.exp(delta / self.T)
                    if np.random.random() < accept_prob:
                        self.current_plan = new_plan
                        current_score = new_score
                        current_success = new_success
                        current_std = new_std
                        current_gap = new_gap
                        current_penalty = new_penalty

                        self.accepted_count += 1
                        phase_accepted_count += 1
                        accepted_in_temp += 1

            # 降温
            self.T *= self.alpha

            # 每10个温度打印一次信息
            if verbose and temperature_count % 10 == 0:
                elapsed = time.time() - start_time
                print(f"[阶段{phase}-温度#{temperature_count}] T={self.T:.2f}, "
                      f"接受率={accepted_in_temp}/{self.inner_iterations}, "
                      f"改进数={improved_in_temp}, "
                      f"用时={elapsed:.1f}s")

        # 阶段完成
        if verbose:
            best_score, best_success, best_std, best_gap, best_penalty = \
                self.calculate_objective(self.best_plan, phase=phase)
            print(f"\n阶段{phase}完成！")
            print(f"阶段迭代次数：{phase_iteration_count}")
            print(
                f"阶段接受次数：{phase_accepted_count} ({phase_accepted_count / max(phase_iteration_count, 1) * 100:.1f}%)")
            print(f"阶段改进次数：{phase_improved_count}")
            print(f"最优解：成功率={best_success:.4f}, 负载标准差={best_std:.4f}, "
                  f"负载差距={best_gap:.4f}, 惩罚={best_penalty:.0f}")
            print(f"阶段用时：{time.time() - start_time:.1f}秒")

        return self.best_plan, True

    # ========== 【改进2-5结束】 ==========

    def optimize(self, max_time=300, verbose=True):
        """
        执行分阶段模拟退火优化

        参数：
        max_time - 最大运行时间（秒）
        verbose - 是否打印详细信息

        返回：优化后的方案
        """
        overall_start_time = time.time()

        if verbose:
            print("\n" + "=" * 70)
            print("开始分阶段模拟退火优化 - 优先级2改进版")
            print("=" * 70)

        # 记录初始解的指标
        initial_score, initial_success, initial_std, initial_gap, initial_penalty = \
            self.calculate_objective(self.current_plan, phase=2)

        if verbose:
            print(f"初始解指标：")
            print(f"  成功率={initial_success:.4f}")
            print(f"  负载标准差={initial_std:.4f}")
            print(f"  负载差距={initial_gap:.4f}")
            print(f"  惩罚={initial_penalty:.0f}")

        # ========== 【改进2-5】分阶段优化 ==========
        # 分配时间：第一阶段40%，第二阶段60%
        phase1_time = max_time * 0.4
        phase2_time = max_time * 0.6

        # 第一阶段：激进均衡
        self.best_plan, _ = self._optimize_single_phase(
            phase=1,
            max_time=phase1_time,
            verbose=verbose
        )

        # 更新当前方案为第一阶段的最优解
        self.current_plan = copy.deepcopy(self.best_plan)

        # 第二阶段：微调优化
        self.best_plan, _ = self._optimize_single_phase(
            phase=2,
            max_time=phase2_time,
            verbose=verbose
        )
        # ========== 【改进2-5结束】 ==========

        # 优化完成
        if verbose:
            print("\n" + "=" * 70)
            print("分阶段优化完成！")
            print("=" * 70)

            # 使用第二阶段的目标函数计算最终指标
            best_score, best_success, best_std, best_gap, best_penalty = \
                self.calculate_objective(self.best_plan, phase=2)

            print(f"总迭代次数：{self.iteration_count}")
            print(f"总接受次数：{self.accepted_count} ({self.accepted_count / self.iteration_count * 100:.1f}%)")
            print(f"总改进次数：{self.improved_count}")
            print(f"\n最优解指标：")
            print(f"  成功率={best_success:.4f}")
            print(f"  负载标准差={best_std:.4f}")
            print(f"  负载差距={best_gap:.4f}")
            print(f"  惩罚={best_penalty:.0f}")
            print(f"  目标函数值={best_score:.2f}")
            print(f"\n总用时：{time.time() - overall_start_time:.1f}秒")

            # 对比初始解
            print(f"\n改进情况：")
            print(f"  成功率: {initial_success:.4f} → {best_success:.4f} "
                  f"({'+' if best_success > initial_success else ''}{(best_success - initial_success) * 100:.2f}%)")
            print(f"  负载标准差: {initial_std:.4f} → {best_std:.4f} "
                  f"({(initial_std - best_std) / initial_std * 100:+.1f}%)")
            print(f"  负载差距: {initial_gap:.4f} → {best_gap:.4f} "
                  f"({(initial_gap - best_gap) / initial_gap * 100:+.1f}%)")
            print("=" * 70)

        return self.best_plan


def optimize_with_sa(all_data, dict_sat_laps_sta_time_all, keys_line,
                     arr_all_start_time, arr_all_end_time, list_cm_avail,
                     initial_plan, satellite_ground_station, num_stations,
                     max_time=300, verbose=True):
    """
    使用分阶段模拟退火优化分配方案

    这是一个便捷的包装函数

    返回：优化后的方案
    """
    sa = SimulatedAnnealing(
        all_data=all_data,
        dict_sat_laps_sta_time_all=dict_sat_laps_sta_time_all,
        keys_line=keys_line,
        arr_all_start_time=arr_all_start_time,
        arr_all_end_time=arr_all_end_time,
        list_cm_avail=list_cm_avail,
        initial_plan=initial_plan,
        satellite_ground_station=satellite_ground_station,
        num_stations=num_stations
    )

    optimized_plan = sa.optimize(max_time=max_time, verbose=verbose)

    return optimized_plan