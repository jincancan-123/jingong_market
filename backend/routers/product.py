from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database.session import get_db
from models.product import Product
from schemas.product import ProductCreate, ProductResponse

router = APIRouter(prefix="/product", tags=["商品管理"])

# 新增商品
@router.post("/", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

# 根据id查询单个商品
@router.get("/{id}", response_model=ProductResponse)
def get_product(id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="该商品不存在")
    return product

# 查询全部商品
@router.get("/", response_model=List[ProductResponse])
def get_all_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

# 修改商品
@router.put("/{id}", response_model=ProductResponse)
def update_product(id: int, product: ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="该商品不存在")
    for k, v in product.model_dump().items():
        setattr(db_product, k, v)
    db.commit()
    db.refresh(db_product)
    return db_product

# 删除商品
@router.delete("/{id}")
def delete_product(id: int, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="该商品不存在")
    db.delete(db_product)
    db.commit()
    return {"msg": "商品删除成功"}