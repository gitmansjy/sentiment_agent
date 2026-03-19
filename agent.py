# agent.py
from database import DatabaseManager
from sentiment import SentimentAnalyzer

# from knowledge_graph import KnowledgeGraphManager   # ← 注释掉导入
from response_generator import ResponseGenerator
from anomaly_detector import AnomalyDetector
from business_integrator import BusinessIntegrator
from continuous_learner import ContinuousLearner
from monitor import OprimionMonitor
from reporter import InsightReporter
from datetime import datetime, timedelta
import config


class OprimionAnalysisAgent:
    def __init__(self):
        self.db = DatabaseManager(config.DB_CONFIG)
        self.analyzer = SentimentAnalyzer(
            config.DASHSCOPE_API_KEY, config.PRODUCT_CATEGORY
        )
        self.monitor = OprimionMonitor(self.db)
        self.reporter = InsightReporter(self.analyzer.llm)
        self.response_gen = ResponseGenerator(self.analyzer.llm)
        self.anomaly_detector = AnomalyDetector(self.db)
        self.business_integrator = BusinessIntegrator(self.db)
        self.learner = ContinuousLearner(self.db, self.analyzer.llm)

        # 注释掉知识图谱初始化
        # if hasattr(config, 'NEO4J_CONFIG'):
        #     self.kg = KnowledgeGraphManager(**config.NEO4J_CONFIG)
        # else:
        #     self.kg = None
        self.kg = None  # 直接设为 None

    def run_once(self, product_id, hours=24):
        print(f"[{datetime.now()}] 开始分析商品 {product_id}...")
        reviews = self.db.fetch_unanalyzed_reviews(product_id, limit=5000)
        if not reviews:
            print("无新评论")
            return
        print(f"获取到 {len(reviews)} 条新评论")

        # 使用并发批量分析
        results = self.analyzer.batch_analyze(reviews, max_workers=5)
        # if self.kg:
        #     entities = self.analyzer.extract_entities(review['content'])
        #     self.kg.add_review_entities(...)
        # 收集所有紧急问题（用于后续预警）
        all_issues = []
        for r in results:
            all_issues.extend(r.get("urgent_issues", []))

        print(f"分析完成: 成功 {len(results)} 条")

        if results:
            self.db.save_analysis_results(results)
            self._update_daily_stats(product_id, results)
        else:
            print("没有成功结果，跳过统计")

        # 异常检测（可选）
        anomaly = self.anomaly_detector.detect_daily(product_id)
        if anomaly and all_issues:
            reply = self.response_gen.generate(reviews[0]["content"], all_issues[0])
            anomaly["reply_draft"] = reply
            self.monitor.trigger_alert(anomaly)

        print("处理完成")

    def _update_daily_stats(self, product_id, results):
        """更新日统计"""
        today = datetime.now().date()
        stats = {
            "total": len(results),
            "positive": sum(1 for r in results if r["overall_sentiment"] == "positive"),
            "neutral": sum(1 for r in results if r["overall_sentiment"] == "neutral"),
            "negative": sum(1 for r in results if r["overall_sentiment"] == "negative"),
            "aspect_scores": {},
            "top_issues": [],
        }

        # 计算各方面平均分
        aspect_counts = {}
        for r in results:
            for aspect, sentiment in r.get("aspects", {}).items():
                if aspect not in stats["aspect_scores"]:
                    stats["aspect_scores"][aspect] = 0
                    aspect_counts[aspect] = 0
                score = (
                    1
                    if sentiment == "positive"
                    else (0.5 if sentiment == "neutral" else 0)
                )
                stats["aspect_scores"][aspect] += score
                aspect_counts[aspect] += 1

        for aspect in stats["aspect_scores"]:
            if aspect_counts[aspect] > 0:
                stats["aspect_scores"][aspect] /= aspect_counts[aspect]

        # 收集紧急问题
        urgent_issues = []
        for r in results:
            urgent_issues.extend(r.get("urgent_issues", []))
        stats["top_issues"] = sorted(
            set(urgent_issues), key=lambda x: urgent_issues.count(x), reverse=True
        )[:10]

        self.db.update_daily_stats(product_id, today, stats)

    def _get_daily_stats(self, product_id, date):
        """获取某天统计（示例）"""
        # 实现略，可从数据库查询
        pass
