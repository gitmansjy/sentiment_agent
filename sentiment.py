# sentiment.py
import dashscope
from dashscope import Generation
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


class DashScopeLLM:
    """通义千问封装"""

    def __init__(self, api_key, model="qwen-plus", temperature=0.2):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def generate(self, prompt):
        response = Generation.call(
            model=self.model,
            prompt=prompt,
            temperature=self.temperature,
            api_key=self.api_key,
        )
        if response.status_code == 200:
            return response.output.text
        else:
            raise Exception(f"API调用失败: {response.message}")


class SentimentAnalyzer:
    """情感分析器（含可解释性）"""

    def __init__(self, api_key, product_category):
        self.llm = DashScopeLLM(api_key)
        self.category = product_category
        # 根据商品类别定义分析维度
        self.aspects_map = {
            "扫地机": ["清洁效果", "路径规划", "续航", "噪音", "越障", "避障"],
            "洗地机": ["吸力", "拖地效果", "自清洁", "水箱容量", "噪音"],
            "吸尘器": ["吸力", "尘杯容量", "过滤效果", "配件丰富度", "轻便性"],
        }
        self.aspects = self.aspects_map.get(product_category, ["质量", "价格", "服务"])

    def analyze_with_evidence(self, review_text):
        """分析评论，返回情感、方面得分及证据句"""
        aspects_str = ", ".join(
            [f'"{a}": "positive/neutral/negative"' for a in self.aspects]
        )
        prompt = f"""
你是一个专业的商品评论分析师。请分析以下关于【{self.category}】的评论，并输出JSON格式结果。

评论内容：{review_text}

要求：
1. 整体情感（positive/neutral/negative）和分数（0最正面1最负面）
2. 各方面情感（{aspects_str}）
3. 每个方面对应的原文证据片段（证明判断的句子）
4. 关键短语（如“电池不耐用”）
5. 紧急问题（如果存在严重负面，否则空数组）

输出格式：
{{
    "overall_sentiment": "positive/neutral/negative",
    "sentiment_score": 0.0-1.0,
    "aspects": {{"性能": "positive/neutral/negative", ...}},
    "evidence": {{"性能": "支持此判断的原文片段", ...}},
    "key_phrases": ["短语1", "短语2"],
    "urgent_issues": ["紧急问题1"]
}}
请只输出JSON，不要其他文字。
"""
        try:
            result_text = self.llm.generate(prompt)
            # 提取JSON
            json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("未找到JSON")
        except Exception as e:
            print(f"分析失败: {e}")
            return self._fallback_analysis()

    def _fallback_analysis(self):
        """API失败时的默认返回"""
        return {
            "overall_sentiment": "neutral",
            "sentiment_score": 0.5,
            "aspects": {a: "neutral" for a in self.aspects},
            "evidence": {a: "" for a in self.aspects},
            "key_phrases": [],
            "urgent_issues": [],
        }

    def extract_entities(self, review_text):
        """抽取部件和问题实体（用于知识图谱）"""
        prompt = f"""
从以下商品评论中抽取涉及的部件/功能名称和用户抱怨的问题描述。
输出JSON格式：{{"parts": ["电池", "屏幕"], "issues": ["续航短", "发烫"]}}
评论：{review_text}
只输出JSON。
"""
        try:
            result = self.llm.generate(prompt)
            json_match = re.search(r"\{.*\}", result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return {"parts": [], "issues": []}

    def batch_analyze(self, reviews, max_workers=5):
        """并发批量分析评论
        :param reviews: list of dict，每个元素必须包含 'id' 和 'content'
        :param max_workers: 并发线程数
        :return: 分析结果列表（与逐条调用格式相同）
        """
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_review = {
                executor.submit(self.analyze_with_evidence, review["content"]): review
                for review in reviews
            }
            for future in as_completed(future_to_review):
                review = future_to_review[future]
                try:
                    analysis = future.result()
                    analysis["review_id"] = review["id"]
                    results.append(analysis)
                except Exception as e:
                    print(f"评论 {review['id']} 分析失败: {e}")
                # 可添加失败重试或日志记录
        return results
