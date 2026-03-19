# monitor.py
from sqlalchemy import text
import json
from datetime import datetime

class OprimionMonitor:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def trigger_alert(self, alert_data):
        """记录预警并发送通知"""
        # 保存到alerts表
        with self.db.engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO alerts 
                    (product_id, alert_level, alert_score, negative_ratio, sample_reviews, reply_draft)
                    VALUES (:pid, :level, :score, :ratio, :samples, :reply)
                """),
                {
                    'pid': alert_data['product_id'],
                    'level': alert_data.get('level', 'yellow'),
                    'score': alert_data.get('score', 0.5),
                    'ratio': alert_data.get('negative_ratio', 0),
                    'samples': json.dumps(alert_data.get('sample_reviews', []), ensure_ascii=False),
                    'reply': alert_data.get('reply_draft', '')
                }
            )
        # 可集成钉钉/邮件通知
        print(f"⚠️ 预警！商品{alert_data['product_id']} 异常")
    
    def check_and_alert(self, product_id, start_date, end_date, negative_ratio_threshold=0.3):
        """检查时间段内负面率是否超阈值"""
        query = text("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN overall_sentiment='negative' THEN 1 ELSE 0 END) as negative_count
            FROM analysis_results a
            JOIN raw_reviews r ON a.review_id = r.id
            WHERE r.product_id = :product_id
              AND r.created_at BETWEEN :start AND :end
        """)
        with self.db.engine.connect() as conn:
            result = conn.execute(query, {
                'product_id': product_id,
                'start': start_date,
                'end': end_date
            }).fetchone()
        
        if result and result[0] > 0:
            negative_ratio = result[1] / result[0]
            if negative_ratio > negative_ratio_threshold:
                # 获取样本评论
                sample_query = text("""
                    SELECT r.content FROM analysis_results a
                    JOIN raw_reviews r ON a.review_id = r.id
                    WHERE r.product_id = :product_id
                      AND r.created_at BETWEEN :start AND :end
                      AND a.overall_sentiment = 'negative'
                    LIMIT 5
                """)
                samples = [row[0] for row in conn.execute(sample_query, {
                    'product_id': product_id,
                    'start': start_date,
                    'end': end_date
                })]
                self.trigger_alert({
                    'product_id': product_id,
                    'level': 'yellow',
                    'score': negative_ratio,
                    'negative_ratio': negative_ratio,
                    'sample_reviews': samples
                })