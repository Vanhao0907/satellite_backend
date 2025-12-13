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
- `DEFAULT_STRATEGY`: 默认调度策略

### 4. 准备数据

将原始Excel数据文件放置在 `data/raw/` 目录下：

```
data/raw/
├── access_1110to1210/
│   ├── QV/
│   │   ├── CM01_QV_access.xlsx
│   │   ├── JMS01_QV_access.xlsx
│   │   └── ...
│   └── S/
│       ├── CQ01_S_access.xlsx
│       └── ...
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

### 执行调度仿真

```http
POST /api/simulations
Content-Type: application/json
```

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| arc_data | string | 是 | 数据集名称（如 "access_1110to1210"） |
| antenna_num | object | 是 | 天线配置对象 |
| time_window | number | 是 | 最小调度窗口时间（秒） |

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
    "task_id": "task_20241212_134523",
    "elapsed_time": 287.5,
    "statistics": {
      "total_tasks": 1500,
      "allocated_tasks": 1434,
      "success_rate_all": 0.956,
      "success_rate_valid": 0.982,
      "climb_success_rate": 0.943,
      "operation_success_rate": 0.967,
      "load_std": 0.023,
      "load_gap": 0.089
    },
    "charts": {
      "gantt_chart_html": "<html>...</html>",
      "satisfaction_chart_html": "<html>...</html>"
    },
    "validation": {
      "no_overflow": true,
      "no_overlap": true,
      "message": "观测时间分配合理"
    }
  }
}
```

---

## 调度策略说明

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
├── app.py                    # Flask应用主入口
├── config.py                 # 全局配置
├── requirements.txt          # 依赖列表
├── .env                      # 环境变量
│
├── api/                      # API接口层
│   └── simulation_api.py
│
├── services/                 # 业务逻辑层
│   └── scheduling_service.py
│
├── core/
│   ├── __init__.py
│   ├── scheduling_algorithm.py  ← 完整版本
│   ├── scheduling/              ← 算法模块目录
│   │   ├── __init__.py
│   │   ├── algorithm.py         ← 从legacy复制
│   │   ├── simulated_annealing.py
│   │   ├── data_processing.py
│   │   ├── validate_results.py
│   │   ├── antenna_load_balance.py
│   │   └── utils.py
│   ├── dataset_builder.py
│   ├── result_combiner.py
│   ├── gantt_chart_generator.py
│   └── satisfaction_chart_generator.py
│
├── data/                     # 数据目录
│   ├── raw/                  # 原始数据
│   └── temp/                 # 临时文件
│
└── logs/                     # 日志文件
```

---

## 开发指南

### 实现业务逻辑

当前项目已搭建好基础框架，业务逻辑使用占位符表示。需要在以下文件中实现具体逻辑：

1. **core/dataset_builder.py**: 实现数据集构建（调用原 dataset.py）
2. **core/scheduling_algorithm.py**: 实现调度算法（调用原 main.py）
3. **core/result_combiner.py**: 实现结果合并（调用原 5result_combine.py）
4. **core/gantt_chart_generator.py**: 实现甘特图生成（调用原 6gantetu.py）
5. **core/satisfaction_chart_generator.py**: 实现满足度图生成（调用原 7manzudu.py）

### 日志管理

日志文件保存在 `logs/app.log`，支持自动滚动（最大10MB，保留5个备份）。

查看日志：
```bash
tail -f logs/app.log
```

### 测试API

使用curl测试：
```bash
curl -X POST http://localhost:5000/api/simulations \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

或使用Postman、Insomnia等工具。

---

## 部署指南

### 生产环境部署

1. **使用Gunicorn启动**:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

2. **配置Nginx反向代理**:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. **使用Supervisor管理进程**（推荐）

---

## 故障排查

### 常见问题

**Q: 启动失败，提示端口已被占用**
```
A: 修改 .env 中的 PORT 配置，或停止占用5000端口的程序
```

**Q: 提示数据集不存在**
```
A: 检查 data/raw/ 目录下是否有对应的数据文件夹
```

**Q: 算法执行超时**
```
A: 增加 .env 中的 REQUEST_TIMEOUT 配置值
```

---

## License

MIT License

---

## 联系方式

- 项目维护者: [Your Name]
- Email: [your-email@example.com]
