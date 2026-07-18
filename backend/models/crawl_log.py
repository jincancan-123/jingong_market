from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database.session import Base

class CrawlLog(Base):
    __tablename__ = "crawl_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_platform = Column(String(50), comment="爬取平台")
    total_num = Column(Integer, default=0, comment="本次采集商品总数")
    success_num = Column(Integer, default=0, comment="成功入库数量")
    status = Column(String(20), comment="执行状态：完成/失败")
    crawl_time = Column(DateTime, default=datetime.now, comment="爬取时间")