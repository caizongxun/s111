"""
【修復版本】app.py - FastAPI 應用

核心修復：
1. ✅ 自動創建不存在的 static 文件夾 (解決 RuntimeError)
2. ✅ 在 startup 時調用 init_fetcher() 初始化全局 Fetcher
3. ✅ 所有端點都通過 get_fetcher() 獲取實例
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional
import os

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 導入配置
from backend.config import (
    API_HOST, API_PORT,
    BINANCE_API_KEY, BINANCE_API_SECRET,
    AUTO_TRADE_ENABLED, USE_TESTNET
)

# 導入後端模塊
from backend.data_fetcher import init_fetcher, get_fetcher
from backend.auto_executor import init_auto_executor, get_auto_executor
from backend.auto_monitor import init_auto_monitor, get_auto_monitor
from backend.time_sync import init_time_sync

# 全局變數
monitor_task = None

async def startup():
    """應用啟動時執行"""
    global monitor_task
    logger.info("=" * 80)
    logger.info("🚀 啟動加密貨幣 LSTM 自動交易系統")
    logger.info("=" * 80)

    try:
        # ✅ Step 1: 初始化全局數據獲取器
        logger.info("1️⃣ 初始化數據獲取器...")
        if not BINANCE_API_KEY or not BINANCE_API_SECRET or "您的" in BINANCE_API_KEY:
             raise ValueError("❌ API Key 或 Secret 未在 config.py 中正確設置！")

        fetcher = init_fetcher(
            api_key=BINANCE_API_KEY,
            api_secret=BINANCE_API_SECRET,
            testnet=USE_TESTNET
        )

        # ✅ Step 2: 初始化時間同步
        logger.info("2️⃣ 初始化時間同步系統...")
        init_time_sync(fetcher.client)

        # ✅ Step 3: 初始化自動交易執行器
        logger.info("3️⃣ 初始化自動交易執行器...")
        init_auto_executor(
            api_key=BINANCE_API_KEY,
            api_secret=BINANCE_API_SECRET,
            testnet=USE_TESTNET,
            stop_loss_percent=0.02,
            take_profit_percent=0.05
        )

        # ✅ Step 4: 初始化自動監控
        logger.info("4️⃣ 初始化自動監控系統...")
        init_auto_monitor()

        # ✅ Step 5: 啟動監控循環
        if AUTO_TRADE_ENABLED:
            logger.info("5️⃣ 啟動自動監控循環...")
            monitor = get_auto_monitor()
            monitor_task = asyncio.create_task(monitor.run_monitoring_loop(interval=60))
        else:
            logger.info("⏭️ 自動交易已禁用")

        logger.info("=" * 80)
        logger.info("✅ 系統啟動完成！")
        logger.info(f"📍 API 地址: http://localhost:{API_PORT}")
        logger.info(f"📚 API 文檔: http://localhost:{API_PORT}/docs")
        logger.info(f"🖥️  前端頁面: http://localhost:{API_PORT}/")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ 啟動失敗: {str(e)}")
        raise

async def shutdown():
    """應用關閉時執行"""
    logger.info("🛑 正在關閉系統...")
    monitor = get_auto_monitor()
    if monitor:
        monitor.stop()
    if monitor_task and not monitor_task.done():
        monitor_task.cancel()
    logger.info("✅ 系統已關閉")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup()
    yield
    await shutdown()

# 創建 FastAPI 應用
app = FastAPI(title="加密貨幣 LSTM 自動交易系統", lifespan=lifespan)

# CORS 中間件
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ✅ 自動創建 static 目錄
static_dir = Path(__file__).parent / "static"
if not static_dir.exists():
    static_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 已自動創建靜態目錄: {static_dir}")

# 掛載靜態文件
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

class OrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: float
    leverage: int = Field(default=1, ge=1, le=125)
    stopLoss: float = Field(default=2.0)
    takeProfit: float = Field(default=5.0)

@app.get("/")
async def read_index():
    # 確保 index.html 存在
    index_file = static_dir / 'index.html'
    if not index_file.exists():
        return {"message": "請將 index.html 放入 backend/static/ 目錄中"}
    return FileResponse(str(index_file))

# ======================== API 端點 ========================

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy"}

@app.get("/account/summary", tags=["Account"])
async def get_account_summary():
    monitor = get_auto_monitor()
    if monitor is None:
        raise HTTPException(status_code=500, detail="Monitor not initialized")
    return monitor.position_monitor.get_account_summary()

@app.post("/place-order", tags=["Trading"])
async def place_order(order: OrderRequest):
    executor = get_auto_executor()
    fetcher = get_fetcher()

    if executor is None or fetcher is None:
        raise HTTPException(status_code=500, detail="System not initialized")

    try:
        current_price = fetcher.get_current_price(order.symbol)
        if current_price is None:
            raise HTTPException(status_code=400, detail=f"無法獲取 {order.symbol} 的價格")

        # 執行下單
        order_response = executor.place_manual_order(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            leverage=order.leverage,
            stop_loss_percent=order.stopLoss,
            take_profit_percent=order.takeProfit,
            current_price=current_price
        )

        return {
            "status": "success",
            "message": "下單成功",
            "order_details": order_response
        }

    except Exception as e:
        logger.error(f"❌ 下單異常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scan-all-signals", tags=["Signals"])
async def scan_all_signals():
    monitor = get_auto_monitor()
    if monitor is None:
        raise HTTPException(status_code=500, detail="Monitor not initialized")
    return monitor.signal_scanner.scan_all_signals()

@app.post("/control/{action}", tags=["Control"])
async def control_service(action: str):
    global monitor_task
    monitor = get_auto_monitor()
    if monitor is None:
        raise HTTPException(status_code=500, detail="Monitor not initialized")

    if action == "start":
        if not monitor.is_running:
            monitor_task = asyncio.create_task(monitor.run_monitoring_loop(interval=60))
            return {"status": "started"}
        return {"status": "already running"}
    elif action == "stop":
        monitor.stop()
        if monitor_task and not monitor_task.done():
            monitor_task.cancel()
        return {"status": "stopped"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

# ======================== 主程序 ========================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level="info"
    )
