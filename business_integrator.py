# business_integrator.py
import pandas as pd

class BusinessIntegrator:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def correlate_with_sentiment(self, product_id, days=30):
        """计算舆情指标与业务指标的相关系数"""
        query = """
            SELECT s.stat_date, 
                   s.negative_count/s.total_reviews as negative_rate,
                   b.sales, b.refund_rate
            FROM sentiment_stats s
            JOIN business_metrics b ON s.product_id = b.product_id AND s.stat_date = b.metric_date
            WHERE s.product_id = %s AND s.stat_date >= CURDATE() - INTERVAL %s DAY
            ORDER BY s.stat_date
        """
        df = pd.read_sql(query, self.db.engine, params=(product_id, days))
        if df.empty or len(df) < 3:
            return {}
        
        corr_neg_sales = df['negative_rate'].corr(df['sales'])
        corr_neg_refund = df['negative_rate'].corr(df['refund_rate'])
        return {
            'negative_sales_corr': corr_neg_sales,
            'negative_refund_corr': corr_neg_refund,
            'data_points': len(df)
        }