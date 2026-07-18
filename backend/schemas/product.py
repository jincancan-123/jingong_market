from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# 新增商品接收参数
class ProductCreate(BaseModel):
    title: str = Field(..., description="商品标题")
    price: float = Field(..., description="商品价格")
    platform: str = Field(..., description="所属平台")
    link: str = Field(..., description="商品链接")
    stock: int = Field(default=0, description="库存数量")

# 返回给前端的完整商品模型
class ProductResponse(ProductCreate):
    id: int
    create_time: Optional[datetime]

    class Config:
      from_attributes = True