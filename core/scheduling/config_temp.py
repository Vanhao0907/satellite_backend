# 临时配置文件 - 由调度服务自动生成
ROOT_FOLDER = r'D:\GitWorkSpace\satellite_backend\data/temp\task_20251213_174005\dataset\access_251213_pro\QV'

OPTIMIZATION = 'TRUE'  # 始终启用优化
METHOD = 3  # 使用method_3（天线均衡优先）
ANSWER_TYPE = 'TRUE'  # 输出Excel格式
USE_SA = 'FALSE'  # 不使用模拟退火
SA_MAX_TIME = 300

# ========== 站内天线负载均衡策略配置 ==========
INTRA_STATION_BALANCE = 'FALSE'  # 不启用站内负载均衡
ANTENNA_LOAD_METHOD = 'B'  # B:时间占用负载
LOAD_WEIGHT_TASK = 0.3
LOAD_WEIGHT_TIME = 0.7
