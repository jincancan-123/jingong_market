from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database.session import get_db
from models.user import User
from schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/user", tags=["后台用户管理"])

# 新增用户
@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # 校验用户名是否重复
    exist_user = db.query(User).filter(User.username == user.username).first()
    if exist_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    db_user = User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# 查询全部用户
@router.get("/", response_model=List[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(User).all()

# 根据id查询用户
@router.get("/{id}", response_model=UserResponse)
def get_user(id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

# 删除用户
@router.delete("/{id}")
def delete_user(id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.delete(user)
    db.commit()
    return {"msg": "用户删除成功"}