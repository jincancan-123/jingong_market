from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from datetime import datetime
from database.session import Base

class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), comment="商品标题")
    price = Column(Float, comment="商品价格")
    platform = Column(String(50), comment="平台名称")
    link = Column(Text, comment="商品链接")
    stock = Column(Integer, default=0, comment="库存")
    # 新增销量、评论数字段
    sales_volume = Column(Integer, default=0, comment="商品销量")
    review_count = Column(Integer, default=0, comment="评论数量")
    create_time = Column(DateTime, default=datetime.now, comment="采集时间")
    brand = Column(String(100), nullable=True, comment="商品品牌，竞品专用")