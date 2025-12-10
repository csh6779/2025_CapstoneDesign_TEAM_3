# server/backend/log.py
import os, json, asyncio, logging
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse

router = APIRouter()

# 로그 파일 경로 (JSON Lines: 한 줄당 하나의 JSON)
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app-log.jsonl"

# 실시간 전달용 큐 (SSE)
log_queue: asyncio.Queue[str] = asyncio.Queue()

def _serialize_record(record: logging.LogRecord) -> dict:
    return {
        "ts": record.created,            # epoch float
        "level": record.levelname,
        "name": record.name,
        "msg": record.getMessage(),
        "module": record.module,
        "func": record.funcName,
        "line": record.lineno,
    }

class JsonLineHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        data = _serialize_record(record)
        # 파일에 JSON 라인으로 append
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        # 실시간 스트림에도 푸시
        try:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(asyncio.create_task, log_queue.put(json.dumps(data)))
        except RuntimeError:
            pass

# 프로젝트 전역에서 import해서 쓸 logger
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
if not any(isinstance(h, JsonLineHandler) for h in logger.handlers):
    h = JsonLineHandler()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    h.setFormatter(fmt)
    logger.addHandler(h)

# === API ===

@router.get("/logs/recent")
def get_recent(limit: int = 200):
    """최근 로그 JSON 줄 N개 반환 (기본 200)"""
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    lines = lines[-limit:]
    return JSONResponse([json.loads(x) for x in lines])

@router.get("/logs/stream")
async def stream_logs():
    """SSE 실시간 로그 스트림 (옵션)"""
    async def gen():
        # 과거 꺼도 보고 싶으면 여기서 file tail 후 먼저 yield 가능
        while True:
            msg = await log_queue.get()
            yield f"data: {msg}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")

@router.post("/logs/test")
async def emit_test_logs():
    logger.info("테스트 로그 - INFO")
    logger.warning("테스트 로그 - WARNING")
    logger.error("테스트 로그 - ERROR")
    return {"ok": True}

@router.delete("/logs/clear")
def clear_logs():
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    LOG_FILE.touch()
    return {"ok": True}
