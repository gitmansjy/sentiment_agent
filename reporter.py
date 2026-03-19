# reporter.py
from datetime import datetime, timedelta

class InsightReporter:
    def __init__(self, llm):
        self.llm = llm
    
    def generate_daily_report(self, product_id, stats, issues):
        """生成日报"""
        prompt = f"""
根据以下商品舆情数据，生成一份简洁的日报：
商品ID：{product_id}
日期：{datetime.now().strftime('%Y-%m-%d')}
评论总数：{stats['total']}
正面：{stats['positive']} 中性：{stats['neutral']} 负面：{stats['negative']}
负面率：{stats['negative']/stats['total']:.2%}
高频问题：{issues[:5]}

请输出报告，包含：
1. 今日舆情概述
2. 主要问题
3. 建议行动
"""
        return self.llm.generate(prompt)
    
    def generate_weekly_trend(self, product_id, daily_stats, business_corr=None):
        """生成周趋势报告"""
        trend_data = {
            'dates': [d['stat_date'] for d in daily_stats],
            'negative_rates': [d['negative']/d['total'] for d in daily_stats]
        }
        prompt = f"""
根据过去一周商品{product_id}的舆情趋势数据，分析趋势并给出建议：
趋势数据：{trend_data}
{f'与业务指标相关性：{business_corr}' if business_corr else ''}
请输出包含趋势分析、拐点识别、原因推测和建议。
"""
        return self.llm.generate(prompt)