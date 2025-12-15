# 卫星资源调度系统 - 后端服务

## 项目简介

本项目是一个卫星资源调度系统的后端服务，提供RESTful API接口，用于执行卫星地面站资源的智能调度分配。

### 核心功能

- **数据集构建**: 将原始Excel数据转换为算法所需的层次化CSV结构
- **智能调度**: 基于贪心算法、迭代优化和模拟退火的多层次调度策略
- **结果合并**: 将调度结果与原始数据合并
- **可视化**: 自动生成甘特图和满足度分析图

### 技术栈

- **Web框架**: Flask 3.0
- **数据处理**: Pandas, NumPy
- **可视化**: Plotly
- **文件格式**: Excel (openpyxl), CSV

---

## 快速开始

### 1. 环境要求

- Python 3.8+
- pip

### 2. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env` 文件并根据需要修改配置：

```bash
cp .env.example .env
```

关键配置项：
- `FLASK_ENV`: 环境模式 (development/production)
- `RAW_DATA_DIR`: 原始数据目录
- `MAX_ANTENNAS_PER_STATION`: 单站最大天线数限制（默认20）

### 4. 准备数据

将原始Excel数据文件放置在 `data/raw/` 目录下：

```
data/raw/
├── access_1110to1210/
│   └── QV/
│       ├── CM01_QV_access.xlsx
│       ├── JMS01_QV_access.xlsx
│       ├── KEL01_QV_access.xlsx
│       ├── KS01_QV_access.xlsx
│       ├── MH01_QV_access.xlsx
│       ├── TC01_QV_access.xlsx
│       ├── WC01_QV_access.xlsx
│       └── XA01_QV_access.xlsx
```

### 5. 启动服务

```bash
python app.py
```

服务将在 `http://localhost:5000` 启动

---

## API文档

### 健康检查

```http
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "message": "服务运行正常"
}
```

---

### 测试接口

```http
GET /api/simulations/test
```

**响应示例**:
```json
{
  "code": 200,
  "message": "仿真API工作正常",
  "data": {
    "endpoint": "/api/simulations",
    "method": "POST",
    "status": "available",
    "version": "QV_ONLY_v2.0",
    "required_params": ["arc_data", "antenna_num", "time_window"],
    "max_antennas_per_station": 20
  }
}
```

---

### 执行调度仿真

```http
POST /api/simulations
Content-Type: application/json
```

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| arc_data | string | 是 | 数据集名称（如 "access_1110to1210"） |
| antenna_num | object | 是 | 天线配置对象（单层结构，仅QV频段） |
| time_window | number | 是 | 最小调度窗口时间（秒），默认300 |

**天线配置说明**:
- 配置为单层对象结构（仅QV频段）
- 支持8个地面站：CM, JMS, KEL, KS, MH, TC, WC, XA
- 每个站点的天线数量必须 ≤ MAX_ANTENNAS_PER_STATION（默认20）

**请求示例**:

```json
{
  "arc_data": "access_1110to1210",
  "antenna_num": {
    "CM": 6,
    "JMS": 14,
    "KEL": 18,
    "KS": 5,
    "MH": 3,
    "TC": 10,
    "WC": 6,
    "XA": 8
  },
  "time_window": 300
}
```

**响应示例**:

```json
{
  "code": 200,
  "message": "卫星资源调度完成",
  "data": {
    "task_id": "task_20241215_134523",
    "elapsed_time": 287.5,
    "statistics": {
      "success_rate_all": 0.956,
      "success_rate_filtered": 0.982,
      "climb_success_rate": 0.943,
      "operation_success_rate": 0.967,
      "total_tasks": 1500,
      "successful_tasks": 1434,
      "load_std": 0.0234,
      "validation": {
        "no_overflow": true,
        "no_overlap": true,
        "message": "验证通过"
      }
    },
    "charts": {
      "gantt_chart_html": "<html>...(完整的甘特图HTML内容)...</html>",
      "satisfaction_chart_html": "<html>...(完整的满足度分析图HTML内容)...</html>"
    },
    "validation": {
      "no_overflow": true,
      "no_overlap": true,
      "message": "验证通过"
    }
  }
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | number | 状态码（200=成功，400=参数错误，404=数据集不存在，500=服务器错误） |
| message | string | 响应消息 |
| data.task_id | string | 任务唯一标识符（格式：task_YYYYMMDD_HHMMSS） |
| data.elapsed_time | number | 调度总耗时（秒） |
| data.statistics.success_rate_all | number | 总体成功率（包含时长不足样本） |
| data.statistics.success_rate_filtered | number | 过滤后成功率（剔除时长不足样本） |
| data.statistics.climb_success_rate | number | climb状态任务成功率 |
| data.statistics.operation_success_rate | number | operation状态任务成功率 |
| data.statistics.total_tasks | number | 总任务数 |
| data.statistics.successful_tasks | number | 成功分配的任务数 |
| data.statistics.load_std | number | 负载标准差（衡量负载均衡程度，越小越好） |
| data.charts.gantt_chart_html | string | 甘特图完整HTML内容（可直接渲染） |
| data.charts.satisfaction_chart_html | string | 满足度分析图完整HTML内容（可直接渲染） |
| data.validation | object | 验证结果信息 |
| data.validation.no_overflow | boolean | 是否存在时间溢出 |
| data.validation.no_overlap | boolean | 是否存在时间重叠 |
| data.validation.message | string | 验证消息 |

**错误响应示例**:

```json
{
  "code": 400,
  "message": "站点 KEL 的天线数量 25 超过系统最大限制 20",
  "data": null
}
```

```json
{
  "code": 404,
  "message": "数据集不存在: access_invalid",
  "data": null
}
```

---

## 调度策略说明

系统实现了三种调度策略（通过`METHOD`配置），默认使用Method 3：

### Method 1: 可分配时间窗口优先
优先选择可观测时间窗口最长的地面站进行分配。

### Method 2: 天线可用率最高优先
优先选择天线可用率最高的地面站进行分配。

### Method 3: 天线均衡优先（推荐）
综合考虑任务数量和时间占用，优先分配给负载较低的地面站，实现全局负载均衡。

---

## 项目结构

```
satellite-scheduling-backend/
├── app.py                          # Flask应用主入口
├── config.py                       # 全局配置（包含MAX_ANTENNAS_PER_STATION等）
├── requirements.txt                # Python依赖列表
├── .env                            # 环境变量配置
├── .gitignore                      # Git忽略文件配置
├── test_api.py                     # API测试脚本
├── test_request.json               # 测试请求数据示例
│
├── api/                            # API接口层
│   ├── __init__.py
│   └── simulation_api.py           # 调度仿真API（POST /api/simulations）
│
├── services/                       # 业务逻辑层
│   ├── __init__.py
│   └── scheduling_service.py       # 调度服务编排（5步流程）
│
├── core/                           # 核心算法模块
│   ├── __init__.py
│   ├── utils.py                    # 通用工具函数
│   ├── dataset_builder.py          # 数据集构建器（步骤1）
│   ├── scheduling_algorithm.py     # 调度算法接口（步骤2）
│   ├── result_combiner.py          # 结果合并器（步骤3）
│   ├── gantt_chart_generator.py    # 甘特图生成器（步骤4）
│   ├── satisfaction_chart_generator.py  # 满足度图生成器（步骤5）
│   ├── gantt_original.py           # 原始甘特图脚本封装
│   ├── satisfaction_original_byhour.py  # 原始满足度图脚本封装
│   │
│   └── scheduling/                 # 底层调度算法模块
│       ├── __init__.py
│       ├── main.py                 # 算法主入口
│       ├── algorithm.py            # 核心调度算法实现
│       ├── data_processing.py      # 数据预处理
│       ├── simulated_annealing.py  # 模拟退火优化
│       ├── validate_results.py     # 结果验证
│       ├── antenna_load_balance.py # 天线负载均衡
│       ├── utils.py                # 算法工具函数
│       ├── config.py               # 算法配置（动态生成）
│       └── legacy_config.py        # 遗留配置参考
│
├── data/                           # 数据目录
│   ├── raw/                        # 原始数据（用户上传）
│   │   └── access_YYMMDD/
│   │       └── QV/
│   │           ├── CM01_QV_access.xlsx
│   │           ├── JMS01_QV_access.xlsx
│   │           └── ...
│   └── temp/                       # 临时文件（自动清理）
│       └── task_YYYYMMDD_HHMMSS/
│           ├── dataset/            # 步骤1输出
│           ├── output/             # 步骤2输出
│           ├── result/             # 步骤3输出
│           └── charts/             # 步骤4-5输出
│
└── logs/                           # 日志目录
    └── app.log                     # 应用日志
```

**目录说明**:

- **api/**: API接口层，处理HTTP请求和响应
- **services/**: 业务逻辑层，编排5步调度流程
- **core/**: 核心功能模块，包含数据处理、算法执行、结果合并和可视化
- **core/scheduling/**: 底层调度算法实现（从遗留代码迁移）
- **data/raw/**: 用户上传的原始Excel数据
- **data/temp/**: 临时工作目录，每个任务独立一个文件夹
- **logs/**: 应用日志，支持滚动（最大10MB，保留5个备份）

**调度流程**:

```
步骤1: DatasetBuilder
  └─ 原始Excel → 层次化CSV数据集

步骤1.5: SchedulingService
  └─ 生成算法配置文件 (core/scheduling/config.py)

步骤2: SchedulingAlgorithm
  └─ CSV数据集 → 调度结果Excel

步骤3: ResultCombiner
  └─ 调度结果 + 原始数据 → 合并数据集

步骤4: GanttChartGenerator
  └─ 合并数据集 → 甘特图HTML

步骤5: SatisfactionChartGenerator
  └─ 合并数据集 → 满足度分析图HTML
```

---

## 配置说明

### 环境变量（.env）

```bash
# Flask配置
FLASK_ENV=development
FLASK_DEBUG=True
HOST=0.0.0.0
PORT=5000

# 目录配置
RAW_DATA_DIR=data/raw
TEMP_DATA_DIR=data/temp
LOG_DIR=logs

# 系统约束
MAX_ANTENNAS_PER_STATION=20  # 单站最大天线数

# 日志配置
LOG_LEVEL=INFO
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=5

# 算法配置
DEFAULT_STRATEGY=method_3
DEFAULT_TIME_WINDOW=300
DEFAULT_OPTIMIZATION=True
DEFAULT_USE_SA=False
DEFAULT_SA_MAX_TIME=300

# 清理策略
AUTO_CLEANUP=False
CLEANUP_KEEP_DAYS=7

# CORS配置
CORS_ORIGINS=*
```

### 算法配置（动态生成）

系统会在每次调度时自动生成 `core/scheduling/config.py`，主要参数包括：

- **ROOT_FOLDER**: 数据集路径（动态生成）
- **TASK_INTERVAL**: 任务间隔时间（来自API参数time_window）
- **OPTIMIZATION**: 是否启用迭代优化（默认TRUE）
- **METHOD**: 调度方法（1/2/3，默认3）
- **USE_SA**: 是否使用模拟退火（默认FALSE）
- **INTRA_STATION_BALANCE**: 站内天线负载均衡（默认FALSE）

---

## 开发指南

### 运行测试

```bash
# 使用测试脚本
python test_api.py

# 使用自定义测试数据
python test_api.py http://localhost:5000 custom_request.json
```

### 查看日志

```bash
# 实时查看日志
tail -f logs/app.log

# 查看最近100行
tail -n 100 logs/app.log
```

### 清理临时文件

```bash
# 手动清理7天前的临时文件
python -c "from core.utils import cleanup_old_tasks; cleanup_old_tasks('data/temp', 7)"
```

---



## 故障排查

### 常见问题

**Q: 启动失败，提示端口已被占用**
```
A: 修改 .env 中的 PORT 配置，或停止占用5000端口的程序
```

**Q: 提示数据集不存在**
```
A: 检查 data/raw/ 目录下是否有对应的数据文件夹，确保路径格式正确
```

**Q: 天线数量超过限制**
```
A: 检查请求中每个站点的天线数量是否超过 MAX_ANTENNAS_PER_STATION（默认20）
   如需调整限制，修改 config.py 中的 MAX_ANTENNAS_PER_STATION 配置
```

**Q: 算法执行超时**
```
A: 增加 .env 中的 REQUEST_TIMEOUT 配置值（秒）
   或在生产环境中增加 Gunicorn 的 --timeout 参数
```

**Q: 图表未生成或显示错误**
```
A: 检查 logs/app.log，确认步骤4-5是否执行成功
   检查 core/gantt_original.py 和 satisfaction_original_byhour.py 是否存在
```

**Q: 配置文件生成失败**
```
A: 检查 logs/app.log 中的步骤1.5日志
   确认 core/scheduling/ 目录有写入权限
   确认 sys.path 配置正确
```

---

## 系统限制

- **单站最大天线数**: 20根（可通过配置调整）
- **支持频段**: 仅QV频段
- **支持站点**: CM, JMS, KEL, KS, MH, TC, WC, XA（共8个）
- **最小观测时间**: 300秒（可通过API参数调整）
- **任务间隔时间**: 300-600秒（根据卫星状态动态调整）
- **日志文件大小**: 单文件最大10MB，保留5个备份
- **临时文件保留**: 默认7天（可配置自动清理）

## 更新日志

### v2.0 (2024-12-15)
- 简化为仅支持QV频段
- 新增单站最大天线数限制（MAX_ANTENNAS_PER_STATION）
- 优化配置文件生成流程
- 改进错误处理和日志记录
- 更新API响应结构
- 修复结果合并器的重复列问题

### v1.0 (2024-11)
- 初始版本发布
- 支持QV和S双频段调度
- 实现基础调度算法和可视化功能