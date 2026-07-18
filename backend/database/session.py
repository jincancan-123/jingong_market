from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from database.config import DATABASE_URL

# 增加连接池保活配置
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_recycle=300,      # 5分钟回收闲置连接
    pool_pre_ping=True     # 自动检测连接有效性
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()