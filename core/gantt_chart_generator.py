"""
甘特图生成器
调用原始脚本生成甘特图
"""
import os
import sys
import logging

logger = logging.getLogger(__name__)


class GanttChartGenerator:
    """甘特图生成器 - 调用原始脚本版本"""

    def __init__(self, result_dir, output_dir):
        """
        初始化生成器

        Args:
            result_dir: 结果数据目录
            output_dir: 图表输出目录
        """
        self.result_dir = result_dir
        self.output_dir = output_dir

        logger.info(f"甘特图生成器初始化（原始脚本版）")
        logger.info(f"  结果目录: {result_dir}")
        logger.info(f"  输出目录: {output_dir}")

    def generate(self):
        """
        生成甘特图 - 直接调用原始脚本

        Returns:
            str: 甘特图HTML内容
        """
        logger.info("=" * 70)
        logger.info("开始生成甘特图...")
        logger.info("=" * 70)

        try:
            # ========== 修复：将 core 目录（当前文件所在目录）添加到路径 ==========
            core_path = os.path.dirname(__file__)  # core/ 目录
            if core_path not in sys.path:
                sys.path.insert(0, core_path)
                logger.info(f"✓ 添加路径到 sys.path: {core_path}")

            # 导入原始脚本封装的函数
            from gantt_original import generate_gantt_chart

            logger.info(f"✓ 成功导入 gantt_original 模块")
            logger.info(f"调用原始甘特图生成函数...")
            logger.info(f"  源目录: {self.result_dir}")
            logger.info(f"  输出目录: {self.output_dir}")

            # 调用原始脚本函数
            html_content = generate_gantt_chart(
                source_dir=self.result_dir,
                output_dir=self.output_dir
            )

            logger.info(f"✓ 甘特图生成完成")
            logger.info(f"  HTML长度: {len(html_content)} 字符")
            logger.info("=" * 70)

            return html_content

        except ImportError as e:
            logger.error(f"导入失败: {e}")
            logger.error(f"当前 sys.path: {sys.path}")
            logger.error(f"__file__: {__file__}")
            logger.error(f"core_path: {os.path.dirname(__file__)}")
            raise

        except Exception as e:
            logger.error(f"甘特图生成失败: {e}", exc_info=True)

            # 返回错误提示的HTML
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>甘特图生成失败</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }}
                    .error-box {{
                        background-color: white;
                        border-left: 4px solid #dc3545;
                        padding: 20px;
                        margin: 20px auto;
                        max-width: 800px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    h2 {{
                        color: #dc3545;
                        margin-top: 0;
                    }}
                    .error-message {{
                        color: #6c757d;
                        background-color: #f8f9fa;
                        padding: 10px;
                        border-radius: 4px;
                        font-family: monospace;
                    }}
                </style>
            </head>
            <body>
                <div class="error-box">
                    <h2>⚠️ 甘特图生成失败</h2>
                    <p><strong>错误信息：</strong></p>
                    <div class="error-message">{str(e)}</div>
                    <p style="margin-top: 20px; color: #6c757d;">
                        请检查日志文件获取详细信息
                    </p>
                </div>
            </body>
            </html>
            """

            return error_html