from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# 新增爬虫日志入参
class CrawlLogCreate(BaseModel):
    target_platform: str = Field(..., description="爬取平台")
    total_num: int = Field(default=0, description="本次采集总数")
    success_num: int = Field(default=0, description="入库成功数")
    status: str = Field(..., description="执行状态：完成/失败")

# 查询返回日志模型
class CrawlLogResponse(CrawlLogCreate):
    id: int
    crawl_time: Optional[datetime]

    class Config:
      from_attributes = True