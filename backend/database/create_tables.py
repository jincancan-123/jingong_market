from database.session import engine, Base
# 必须导入所有模型，SQLAlchemy才能识别表结构
from models.product import Product
from models.crawl_log import CrawlLog
from models.user import User

def create_all_tables():
    # 不存在则创建表，不会删除已有数据
    Base.metadata.create_all(bind=engine)
    print("✅ 所有数据表创建完成！去DBeaver刷新数据库就能看到三张表")

if __name__ == "__main__":
    create_all_tables()