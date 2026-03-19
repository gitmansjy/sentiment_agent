# knowledge_graph.py
from neo4j import GraphDatabase

class KnowledgeGraphManager:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    def add_review_entities(self, review_id, product_id, parts, issues, sentiment):
        """将评论中抽取的实体关系存入图谱"""
        with self.driver.session() as session:
            # 创建产品节点
            session.run("MERGE (p:Product {id: $product_id})", product_id=product_id)
            
            # 处理部件
            for part in parts:
                session.run(
                    """
                    MERGE (pt:Part {name: $part})
                    MERGE (p:Product {id: $product_id})
                    MERGE (p)-[:HAS_PART]->(pt)
                    """,
                    part=part, product_id=product_id
                )
            
            # 处理问题
            for issue in issues:
                session.run("MERGE (i:Issue {description: $issue})", issue=issue)
                session.run(
                    """
                    MATCH (p:Product {id: $product_id})
                    MERGE (i:Issue {description: $issue})
                    MERGE (p)-[:HAS_ISSUE]->(i)
                    """,
                    product_id=product_id, issue=issue
                )
                session.run(
                    """
                    MATCH (i:Issue {description: $issue})
                    CREATE (r:Review {id: $review_id, sentiment: $sentiment})
                    CREATE (r)-[:MENTIONS]->(i)
                    """,
                    issue=issue, review_id=review_id, sentiment=sentiment
                )
    
    def get_top_issues(self, product_id, limit=10):
        """获取某个产品的前N个高频问题"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Product {id: $product_id})-[:HAS_ISSUE]->(i:Issue)<-[:MENTIONS]-(r:Review)
                RETURN i.description as issue, COUNT(r) as count
                ORDER BY count DESC LIMIT $limit
                """,
                product_id=product_id, limit=limit
            )
            return [(record["issue"], record["count"]) for record in result]