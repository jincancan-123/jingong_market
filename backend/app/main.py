from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.health import router as health_router
from routers.product import router as product_router
from routers.crawl_log import router as log_router
from routers.user import router as user_router
from routers.crawl import router as crawl_router
from utils.scheduler import start_scheduler
from routers.process import router as process_router
from routers.dashboard import router as dashboard_router
from routers.report import router as report_router
from routers.alert import router as alert_router
from routers.miniapp import router as miniapp_router

# 启动定时任务调度器
start_scheduler()

app = FastAPI(title="jinggong_market backend", version="0.1.0")

# 【新增】允许前端跨域调用，大屏页面必配
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
# 挂载业务接口
app.include_router(product_router)
app.include_router(log_router)
app.include_router(user_router)
app.include_router(crawl_router)
app.include_router(process_router)
# 【新增】挂载可视化大屏接口
app.include_router(dashboard_router)
app.include_router(report_router)
app.include_router(alert_router)
app.include_router(miniapp_router)

@app.get("/")
async def root() -> dict:
    return {"message": "FastAPI backend skeleton is running"}