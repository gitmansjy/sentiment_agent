# response_generator.py
class ResponseGenerator:
    def __init__(self, llm):
        self.llm = llm
    
    def generate(self, review_text, issue_type=None):
        prompt = f"""
你是一个专业的客服助手，请针对以下用户评论生成一条礼貌、专业的回复。
要求：
- 承认用户的问题
- 表达歉意
- 提供帮助或解决方案
- 保持品牌语气（热情、专业）

评论：{review_text}
{f'问题类型：{issue_type}' if issue_type else ''}

回复：
"""
        return self.llm.generate(prompt)