"""
满足度分析图生成 - 原始脚本封装版
基于原始脚本: 8manzudu_groupbyday.py
功能: 将原始脚本封装为可调用的函数，几乎不修改核心逻辑
"""
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def generate_satisfaction_chart(source_dir, output_dir):
    """
    生成满足度分析图

    参数:
    source_dir: 结果CSV文件所在目录
    output_dir: HTML输出目录

    返回:
    str: 满足度图HTML内容
    """
    # ========== 以下代码几乎完全来自原始 8manzudu_groupbyday.py ==========

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    print(f"开始分析: {source_dir}")

    # 第一步: 收集所有 CSV 文件并读取数据
    all_data = []
    antenna_mapping = {}  # 存储天线编号映射

    # 卫星类型定义
    test_sats = {"A0001", "A0002", "A0004", "B0001", "B0002", "B0003", "B0004",
                 "B0005", "B0006", "B0013"}

    # 遍历目录
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.csv'):
                file_path = os.path.join(root, file)
                print(f"正在处理: {file_path}")
                try:
                    # 读取 CSV 文件
                    df = pd.read_csv(file_path)

                    # 获取相对路径并生成天线编号
                    rel_path = os.path.relpath(root, source_dir)
                    antenna_id = rel_path.replace(os.sep, '_') + '_' + file.split('_')[0]

                    # 添加天线编号和文件路径信息
                    df['antenna_id'] = antenna_id
                    df['file_path'] = file_path

                    # 添加日期时间信息
                    df['start'] = pd.to_datetime(df['start'], errors='coerce')
                    df['stop'] = pd.to_datetime(df['stop'], errors='coerce')
                    df['date'] = df['start'].dt.date
                    df['hour'] = df['start'].dt.hour

                    # 标记测控是否成功 (allocation_status 在 1-4 范围内)
                    df['success'] = df['allocation_status'].apply(lambda x: 1 if x in [1, 2, 3, 4] else 0)

                    # 确定卫星类型
                    def get_sat_type(sat):
                        if sat in test_sats:
                            return "Test Star"
                        elif sat.startswith('A'):
                            return "Proximal Constellations"
                        elif sat.startswith('B'):
                            return "Inclined constellation"
                        elif sat.startswith('X'):
                            return "Star X"
                        else:
                            return "Other"

                    df['sat_type'] = df['sat'].apply(get_sat_type)

                    all_data.append(df)
                    antenna_mapping[antenna_id] = file_path
                    print(f"加载完成: {file_path}")

                except Exception as e:
                    print(f"读取文件失败: {file_path} | {e}")

    if not all_data:
        print("警告: 未找到CSV文件")
        # 返回空白图表
        return """
        <!DOCTYPE html>
        <html>
        <head><title>满足度分析图</title></head>
        <body>
            <h2 style="text-align:center; color:#6C757D;">未找到数据</h2>
            <p style="text-align:center;">未找到任何 CSV 文件</p>
        </body>
        </html>
        """

    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"合并数据: {len(combined_df)} 行")

    # 第二步: 按照新逻辑处理数据
    print("\n按照新逻辑处理数据...")

    # 步骤1: 获取所有测控成功的(sat, laps)组合
    success_records = combined_df[combined_df['success'] == 1]
    success_keys = success_records[['sat', 'laps']].drop_duplicates()
    print(f"测控成功的(sat, laps)组合数量: {len(success_keys)}")

    # 步骤2: 从所有数据中剔除成功组合中不成功的数据行
    # 创建合并键
    combined_df['key'] = combined_df['sat'] + '_' + combined_df['laps'].astype(str)
    success_keys['key'] = success_keys['sat'] + '_' + success_keys['laps'].astype(str)

    # 标记需要保留的数据行:
    # 1. 所有成功记录
    # 2. 不在成功组合中的记录
    mask = (~combined_df['key'].isin(success_keys['key'])) | (combined_df['success'] == 1)
    filtered_df = combined_df[mask].copy()
    print(f"过滤后的数据行数: {len(filtered_df)} (移除了 {len(combined_df) - len(filtered_df)} 行)")

    # 步骤3: 对于剩下的数据，找出每个(sat, laps)组合时间最早的那条数据
    # 对于没有成功记录的(sat, laps)组合，取最早的一条
    earliest_records = filtered_df.sort_values('start').groupby(['sat', 'laps']).first().reset_index()
    print(f"获取到的最早记录数量: {len(earliest_records)}")

    # 步骤4: 合并三部分数据
    # 注意: 这里我们只需要最早记录，因为成功记录已经在最早记录中（如果成功记录是最早的）
    final_df = earliest_records
    print(f"最终数据集大小: {len(final_df)}")

    # 第三步: 生成图表 1 - 测控任务满足度分析图(按天统计)
    print("\n生成图表: 测控任务满足度分析图(按天统计)")

    # 按天统计需求圈次数（所有记录）
    demand_df = final_df.groupby('date').size().reset_index(name='demand_count')

    # 按天统计成功圈次数
    success_df = final_df[final_df['success'] == 1]
    success_count = success_df.groupby('date').size().reset_index(name='success_count')

    # 合并需求数和成功数
    daily_df = pd.merge(demand_df, success_count, on='date', how='left').fillna(0)

    # 计算满足率
    daily_df['satisfaction_rate'] = daily_df['success_count'] / daily_df['demand_count'] * 100

    # 计算整体平均满足率
    total_demand = daily_df['demand_count'].sum()
    total_success = daily_df['success_count'].sum()
    avg_satisfaction = (total_success / total_demand * 100) if total_demand > 0 else 0
    print(f"整体平均满足率: {avg_satisfaction:.2f}%")

    # 创建图表
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])

    # 添加柱状图 (需求圈次)
    fig1.add_trace(
        go.Bar(
            x=daily_df['date'],
            y=daily_df['demand_count'],
            name='需求圈次',
            marker_color='#1f77b4',
            opacity=0.7
        ),
        secondary_y=False
    )

    # 添加折线图 (成功圈次)
    fig1.add_trace(
        go.Scatter(
            x=daily_df['date'],
            y=daily_df['success_count'],
            name='成功圈次',
            mode='lines+markers',
            line=dict(color='#ff7f0e', width=3),
            marker=dict(size=8, symbol='diamond')
        ),
        secondary_y=False
    )

    # 添加满足率折线图 (使用第二个 Y 轴)
    fig1.add_trace(
        go.Scatter(
            x=daily_df['date'],
            y=daily_df['satisfaction_rate'],
            name='满足率',
            mode='lines+markers',
            line=dict(color='#2ca02c', width=2, dash='dot'),
            marker=dict(size=6, symbol='circle')
        ),
        secondary_y=True
    )

    # 添加平均满足率注释
    fig1.add_annotation(
        x=daily_df['date'].max(),
        y=avg_satisfaction,
        text=f"平均满足率: {avg_satisfaction:.2f}%",
        showarrow=True,
        arrowhead=1,
        ax=-100,
        ay=0,
        bgcolor="white",
        bordercolor="red",
        borderwidth=1,
        secondary_y=True
    )

    # 添加总需求圈次和总成功圈次注释
    fig1.add_annotation(
        x=0,
        y=1.1,
        xref="paper",
        yref="paper",
        text=f"总需求圈次: {int(total_demand)}, 总成功圈次: {int(total_success)}",
        showarrow=False,
        align="left",
        bgcolor="white",
        bordercolor="blue",
        borderwidth=1
    )

    # 设置图表布局
    fig1.update_layout(
        title={
            'text': f"测控任务满足度分析(按天统计) (平均满足率: {avg_satisfaction:.2f}%)",
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title='日期',
        yaxis_title='圈次数量',
        template='plotly_white',
        hovermode='x unified',
        legend_title_text='指标',
        barmode='group',
        height=600,
        width=1200,  # 增加宽度以适应日期显示
        margin=dict(t=100, b=80, l=50, r=50)  # 调整边距
    )

    # 设置第二个 Y 轴
    fig1.update_yaxes(title_text="满足率 (%)", secondary_y=True, range=[0, 100])
    fig1.update_yaxes(title_text="圈次数量", secondary_y=False)

    # 改善日期显示
    # 计算要显示的日期间隔（例如每15天显示一次）
    date_range = pd.date_range(start=daily_df['date'].min(), end=daily_df['date'].max())
    display_dates = date_range[::15]  # 每15天显示一个标签

    fig1.update_xaxes(
        tickformat="%Y-%m-%d",
        tickangle=45,
        tickvals=display_dates,  # 指定要显示的具体日期
        ticktext=[d.strftime("%Y-%m-%d") for d in display_dates],  # 指定显示的文本
        nticks=len(display_dates)  # 设置显示的刻度数量
    )

    # ========== 修改部分：返回HTML而不是显示 ==========
    # 生成 HTML 内容
    html_content = fig1.to_html(
        include_plotlyjs='cdn',
        config={'displayModeBar': True, 'responsive': True}
    )

    # 同时保存文件（保持原有功能）
    chart_path = os.path.join(output_dir, "satisfaction_chart.html")
    fig1.write_html(chart_path)
    print(f"满足度图已保存: {chart_path}")

    # 同时保存处理后的数据用于验证
    final_df_path = os.path.join(output_dir, "processed_data_control.csv")
    final_df.to_csv(final_df_path, index=False)
    print(f"处理后的数据已保存: {final_df_path}")

    # 返回 HTML 内容
    return html_content


def main():
    """
    独立测试函数
    """
    import sys

    if len(sys.argv) < 3:
        print("用法: python satisfaction_original.py <source_dir> <output_dir>")
        sys.exit(1)

    source_dir = sys.argv[1]
    output_dir = sys.argv[2]

    html_content = generate_satisfaction_chart(source_dir, output_dir)
    print(f"\n✓ 满足度分析图生成完成")
    print(f"HTML长度: {len(html_content)} 字符")


if __name__ == '__main__':
    main()