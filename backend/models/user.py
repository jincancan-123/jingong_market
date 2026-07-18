from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database.session import Base

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, comment="用户名")
    password = Column(String(128), comment="密码")
    create_time = Column(DateTime, default=datetime.now)