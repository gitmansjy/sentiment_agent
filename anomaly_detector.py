# anomaly_detector.py
import pandas as pd
from prophet import Prophet
from datetime import datetime, timedelta

class AnomalyDetector:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def detect_daily(self, product_id):
        """检测昨日是否异常"""
        query = """
            SELECT stat_date, total_reviews, negative_count/total_reviews as negative_rate
            FROM sentiment_stats
            WHERE product_id = %s AND stat_date >= CURDATE() - INTERVAL 30 DAY
            ORDER BY stat_date
        """
        df = pd.read_sql(query, self.db.engine, params=(product_id,))
        if len(df) < 7:
            return None  # 数据不足
        
        # 重命名列以适应Prophet
        df_prophet = df.rename(columns={'stat_date': 'ds', 'negative_rate': 'y'})
        
        # 训练模型
        model = Prophet()
        model.fit(df_prophet)
        
        # 预测昨天
        yesterday = datetime.now().date() - timedelta(days=1)
        future = pd.DataFrame({'ds': [yesterday]})
        forecast = model.predict(future)
        pred = forecast.iloc[0]
        
        # 获取实际值
        actual_row = df[df['stat_date'] == yesterday]
        if actual_row.empty:
            return None
        actual = actual_row['negative_rate'].values[0]
        
        # 判断是否异常（超出预测区间）
        lower = pred['yhat_lower']
        upper = pred['yhat_upper']
        if actual < lower or actual > upper:
            return {
                'product_id': product_id,
                'date': str(yesterday),
                'actual': actual,
                'predicted': pred['yhat'],
                'lower': lower,
                'upper': upper,
                'deviation': actual - pred['yhat']
            }
        return None