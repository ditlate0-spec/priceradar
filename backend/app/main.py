from contextlib import asynccontextmanager
from datetime import datetime, timezone

import asyncio
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import text

from app.api.spreads import router as spreads_router
from app.api.peaks import router as peaks_router
from app.api.history import router as history_router
from app.api.heatmap import router as heatmap_router
from app.collectors.manager import collector_manager
from app.core.aggregator import aggregator_loop
from app.core.app_state import get_app_state, init_app_state
from app.core.config import get_settings
from app.core.database import dispose_db, get_session_factory, init_db
from app.core.peak_detector import peak_detector_loop
from app.core.store import price_store
from app.core.tick_processor import tick_loop
from app.api.export import router as export_router
from app.api.fees import router as fees_router

logger.remove()
logger.add(
    sys.stdout,
    level=get_settings().log_level,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PriceRadar backend starting...")
    settings = get_settings()
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"Threshold version: {settings.threshold_version}")

    # 1. БД
    await init_db()

    # 2. Коллекторы
    await collector_manager.start()

    # 3. AppState + фоновые таски
    state = init_app_state()
    state.started_at = datetime.now(timezone.utc)

    state.tick_task = asyncio.create_task(tick_loop(state), name="tick_processor")
    logger.info("tick_processor запущен")

    state.aggregator_task = asyncio.create_task(
        aggregator_loop(state), name="aggregator"
    )
    logger.info("aggregator запущен")

    state.peak_detector_task = asyncio.create_task(
        peak_detector_loop(state), name="peak_detector"
    )
    logger.info("peak_detector запущен")

    yield

    logger.info("PriceRadar backend shutting down...")

    # Останавливаем фоновые таски
    for task in (
        state.tick_task,
        state.aggregator_task,
        state.peak_detector_task,
    ):
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    await collector_manager.stop()
    await dispose_db()


app = FastAPI(
    title="PriceRadar API",
    version="1.0.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spreads_router)
app.include_router(peaks_router)
app.include_router(history_router)
app.include_router(heatmap_router)
app.include_router(export_router)
app.include_router(fees_router)

@app.get("/api/v1/health")
async def health():
    settings = get_settings()

    db_status = "ok"
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {e.__class__.__name__}"
        logger.error(f"DB health check failed: {e}")

    # Статус коллекторов
    exchanges_status = {}
    for collector in collector_manager.collectors:
        count = len(price_store.get_all_for_exchange(collector.exchange))
        exchanges_status[collector.exchange] = {
            "running": collector._running,
            "tickers": count,
        }

    # Статус секундных буферов
    buffer_ready = False
    buffer_eta_seconds = 300
    buffers_count = 0
    buffer_min_size = 0
    open_peaks_count = 0
    try:
        state = get_app_state()
        bm = state.buffer_manager
        buffers_count = len(bm.all_row_ids())
        buffer_min_size = bm.min_size()
        buffer_ready = bm.is_ready(min_points=300)
        buffer_eta_seconds = 0 if buffer_ready else max(0, 300 - buffer_min_size)
        open_peaks_count = len(state.open_peaks)
    except RuntimeError:
        pass

    return {
        "status": "ok",
        "version": "1.0.0",
        "db": db_status,
        "exchanges": exchanges_status,
        "buffers_count": buffers_count,
        "buffer_min_size": buffer_min_size,
        "buffer_ready": buffer_ready,
        "buffer_eta_seconds": buffer_eta_seconds,
        "open_peaks": open_peaks_count,
        "threshold_version": settings.threshold_version,
        "fees": {
            "binance": settings.fee_binance,
            "bybit": settings.fee_bybit,
            "okx": settings.fee_okx,
        },
    }