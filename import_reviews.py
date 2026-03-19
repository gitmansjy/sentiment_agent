# import_reviews.py
import pandas as pd
from sqlalchemy import create_engine, text
import config
from datetime import datetime

# 数据库连接
engine = create_engine(
    f"mysql+pymysql://{config.DB_CONFIG['user']}:{config.DB_CONFIG['password']}@"
    f"{config.DB_CONFIG['host']}:{config.DB_CONFIG['port']}/{config.DB_CONFIG['database']}"
)

# 读取CSV文件
csv_file = "xhs_691554c0000000000503bdc6_20260319_173805.csv"
df = pd.read_csv(csv_file, encoding="utf-8-sig")

print(f"CSV总行数: {len(df)}")
print("列名:", df.columns.tolist())

# 重命名列以匹配数据库字段
column_mapping = {
    "类型": "comment_type",
    "评论ID": "original_comment_id",
    "用户名称": "user_name",
    "用户ID": "user_id",
    "评论内容": "content",
    "点赞数": "like_count",
    "IP属地": "ip_location",
    "发布时间": "created_at",
    "父评论ID": "parent_comment_id",
    "回复对象": "reply_to_user",
}
df.rename(columns=column_mapping, inplace=True)

# 数据清洗
df["original_comment_id"] = df["original_comment_id"].astype(str).str.strip()
df["user_id"] = df["user_id"].astype(str).str.strip()
# 父评论ID：空值处理为None，非空保留字符串
df["parent_comment_id"] = df["parent_comment_id"].apply(
    lambda x: str(x).strip() if pd.notna(x) and str(x).strip() != "" else None
)
df["like_count"] = df["like_count"].fillna(0).astype(int)
df["ip_location"] = df["ip_location"].fillna("未知")
df["reply_to_user"] = df["reply_to_user"].fillna("")

# 处理发布时间：转换为datetime
df["created_at"] = pd.to_datetime(
    df["created_at"], format="%Y-%m-%d %H:%M:%S", errors="coerce"
)

# 添加固定字段
df["platform"] = "小红书"
df["product_id"] = "扫地机器人"  # 可根据需要修改
df["collected_at"] = datetime.now()

# 准备插入数据
insert_data = []
for _, row in df.iterrows():
    if pd.isna(row["created_at"]):
        print(f"跳过无效日期行: {row['original_comment_id']}")
        continue
    insert_data.append(
        {
            "original_comment_id": row["original_comment_id"],
            "platform": row["platform"],
            "product_id": row["product_id"],
            "user_id": row["user_id"],
            "user_name": row["user_name"],
            "content": row["content"],
            "like_count": row["like_count"],
            "ip_location": row["ip_location"],
            "created_at": row["created_at"],
            "parent_comment_id": row["parent_comment_id"],
            "reply_to_user": row["reply_to_user"],
            "collected_at": row["collected_at"],
        }
    )

print(f"准备插入 {len(insert_data)} 条记录")

# 批量插入
batch_size = 1000
with engine.begin() as conn:
    for i in range(0, len(insert_data), batch_size):
        batch = insert_data[i : i + batch_size]
        conn.execute(
            text(
                """
                INSERT INTO raw_reviews 
                (original_comment_id, platform, product_id, user_id, user_name, content, like_count, ip_location, created_at, parent_comment_id, reply_to_user, collected_at)
                VALUES (:original_comment_id, :platform, :product_id, :user_id, :user_name, :content, :like_count, :ip_location, :created_at, :parent_comment_id, :reply_to_user, :collected_at)
            """
            ),
            batch,
        )
        print(f"已插入 {i+len(batch)} 条")

print("✅ 数据导入完成！")
