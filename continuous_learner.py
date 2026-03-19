# continuous_learner.py
import pandas as pd

class ContinuousLearner:
    def __init__(self, db_manager, llm):
        self.db = db_manager
        self.llm = llm
    
    def collect_feedback(self, days=7):
        """获取最近days天的人工反馈数据"""
        query = """
            SELECT r.content, f.original_sentiment, f.corrected_sentiment, f.corrected_aspects
            FROM feedback f
            JOIN raw_reviews r ON f.review_id = r.id
            WHERE f.created_at >= NOW() - INTERVAL %s DAY
        """
        df = pd.read_sql(query, self.db.engine, params=(days,))
        return df
    
    def generate_few_shot_examples(self):
        """从反馈中生成Few-shot示例，可用于优化Prompt"""
        df = self.collect_feedback()
        examples = []
        for _, row in df.iterrows():
            examples.append({
                'review': row['content'],
                'corrected_sentiment': row['corrected_sentiment'],
                'corrected_aspects': row['corrected_aspects']
            })
        return examples[:5]  # 返回前5条作为示例