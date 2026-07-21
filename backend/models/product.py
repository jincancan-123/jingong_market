from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Index
from datetime import datetime
from database.session import Base

class Product(Base):
    __tablename__ = "product"
    __table_args__ = (
        # 优化点4：复合索引，覆盖 create_time + 分组字段，提升时间窗口下的平台/品牌聚合性能
        Index("ix_product_create_time_platform", "create_time", "platform"),
        Index("ix_product_create_time_brand", "create_time", "brand"),
    )

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