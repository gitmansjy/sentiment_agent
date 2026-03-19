# config.py
import os

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'a123456',
    'database': 'review_analysis'
}

# 通义千问API密钥
DASHSCOPE_API_KEY = '替换为您的密钥'  # 替换为您的密钥

# Neo4j图数据库配置（可选）
NEO4J_CONFIG = {
    'uri': 'bolt://localhost:7687',
    'user': 'neo4j',
    'password': 'your_neo4j_password'
}

# 商品类别（用于方面级分析）
PRODUCT_CATEGORY = '清洁电器'  # 可改为其他
