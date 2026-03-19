# database.py
from sqlalchemy import create_engine, text
import pandas as pd
import json
from datetime import datetime

class DatabaseManager:
    def __init__(self, config):
        self.engine = create_engine(
            f"mysql+pymysql://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )
    
    def fetch_unanalyzed_reviews(self, product_id, limit=1000):
        """获取未分析的新评论"""
        query = text("""
            SELECT r.* FROM raw_reviews r
            LEFT JOIN analysis_results a ON r.id = a.review_id
            WHERE r.product_id = :product_id
              AND a.id IS NULL
              AND r.created_at >= NOW() - INTERVAL 90 DAY
            ORDER BY r.created_at DESC
            LIMIT :limit
        """)
        df = pd.read_sql(query, self.engine, params={'product_id': product_id, 'limit': limit})
        return df.to_dict('records')
    
    def save_analysis_results(self, results):
        """批量保存分析结果"""
        with self.engine.begin() as conn:
            for res in results:
                conn.execute(
                    text("""
                        INSERT INTO analysis_results 
                        (review_id, overall_sentiment, sentiment_score, aspects, key_phrases, urgent_issues, evidence)
                        VALUES (:review_id, :overall_sentiment, :sentiment_score, :aspects, :key_phrases, :urgent_issues, :evidence)
                    """),
                    {
                        'review_id': res['review_id'],
                        'overall_sentiment': res['overall_sentiment'],
                        'sentiment_score': res['sentiment_score'],
                        'aspects': json.dumps(res.get('aspects', {}), ensure_ascii=False),
                        'key_phrases': json.dumps(res.get('key_phrases', []), ensure_ascii=False),
                        'urgent_issues': json.dumps(res.get('urgent_issues', []), ensure_ascii=False),
                        'evidence': json.dumps(res.get('evidence', {}), ensure_ascii=False)
                    }
                )
    
    def update_daily_stats(self, product_id, stat_date, stats):
        """更新日统计表"""
        query = text("""
            INSERT INTO sentiment_stats 
            (product_id, stat_date, total_reviews, positive_count, neutral_count, negative_count, aspect_scores, top_issues)
            VALUES (:product_id, :stat_date, :total, :pos, :neu, :neg, :aspects, :issues)
            ON DUPLICATE KEY UPDATE
                total_reviews = VALUES(total_reviews),
                positive_count = VALUES(positive_count),
                neutral_count = VALUES(neutral_count),
                negative_count = VALUES(negative_count),
                aspect_scores = VALUES(aspect_scores),
                top_issues = VALUES(top_issues)
        """)
        with self.engine.begin() as conn:
            conn.execute(query, {
                'product_id': product_id,
                'stat_date': stat_date,
                'total': stats['total'],
                'pos': stats['positive'],
                'neu': stats['neutral'],
                'neg': stats['negative'],
                'aspects': json.dumps(stats.get('aspect_scores', {})),
                'issues': json.dumps(stats.get('top_issues', [])[:10])
            })
    
    def save_feedback(self, feedback):
        """保存人工反馈"""
        query = text("""
            INSERT INTO feedback 
            (review_id, original_sentiment, corrected_sentiment, corrected_aspects, reviewer)
            VALUES (:review_id, :original_sentiment, :corrected_sentiment, :corrected_aspects, :reviewer)
        """)
        with self.engine.begin() as conn:
            conn.execute(query, feedback)