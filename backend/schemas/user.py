from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# 创建用户提交参数
class UserCreate(BaseModel):
    username: str = Field(..., description="登录用户名")
    password: str = Field(..., description="登录密码")

# 返回用户信息（不返回密码）
class UserResponse(BaseModel):
    id: int
    username: str
    create_time: Optional[datetime]

    class Config:
      from_attributes = True