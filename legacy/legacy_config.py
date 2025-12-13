ROOT_FOLDER1 = 'D:\\GitWorkSpace\\TimeAllocation_0802\\access_250805_pro\\QV'
ROOT_FOLDER2 = 'D:\\GitWorkSpace\\TimeAllocation_0802\\access_250805_pro\\S'

OPTIMIZATION = 'TRUE' # 选择TRUE时，method有明显效果
METHOD = 3 # 1:可分配时间窗口优先；2：天线可用率最高优先；3：天线均衡优先
ANSWER_TYPE = 'TRUE' # 选择TRUE时，结果输出为EXCEL表格
USE_SA = 'FALSE'        # 启用SA优化
SA_MAX_TIME = 300      # 5分钟标准配置

# ========== 站内天线负载均衡策略配置 ==========
INTRA_STATION_BALANCE = 'False'  # 启用站内天线负载均衡
ANTENNA_LOAD_METHOD = 'B'  # A:任务数量负载；B:时间占用负载；C:综合负载(推荐)
# 方案C的权重配置（仅当ANTENNA_LOAD_METHOD='C'时生效）
LOAD_WEIGHT_TASK = 0.3      # 任务数量权重
LOAD_WEIGHT_TIME = 0.7      # 时间占用权重

