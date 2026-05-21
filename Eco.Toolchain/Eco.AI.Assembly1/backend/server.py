import os
import sys
import json
import asyncio
import logging
from pathlib import Path

# Add project root to PYTHONPATH for agent imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict, Any, AsyncGenerator, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

# Import agent
from agent.chat_agent import create_chat_agent, ChatContext
from agent.main import get_llm

load_dotenv()

logger = logging.getLogger(__name__)

# RAG init status
rag_init_status = {"running": False, "progress": 0, "message": "", "error": None}

app = FastAPI(title="EcoOS Agent API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount output files
os.makedirs("output", exist_ok=True)
app.mount("/files", StaticFiles(directory="output"), name="files")

# Initialize chat agent (V4: Architect + Coders)
llm = get_llm()
chat_agent = create_chat_agent(llm)


# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE SESSION — decouples LangGraph from WebSocket lifecycle
# ═══════════════════════════════════════════════════════════════════════════

class PipelineSession:
    """
    Holds a running pipeline's event stream.
    Pipeline emits events → stored in buffer + pushed to all subscriber queues.
    WebSocket clients subscribe/unsubscribe without affecting pipeline execution.

    V4: interrupt/resume is handled inside chat_agent (GraphInterrupt catch).
    Server only needs to forward prd_approve/reject as new user messages.

    """

    def __init__(self):
        self.events: list[dict] = []
        self.subscribers: set[int] = set()  # queue IDs
        self._queues: dict[int, asyncio.Queue] = {}
        self._next_id = 0
        self.is_done = False
        self.task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def emit(self, event: dict):
        """Emit event to buffer + all active subscribers.

        Lock guarantees buffer order matches subscriber-queue order even when
        multiple coroutines emit concurrently for the same thread_id.
        """
        etype = event.get("type", "?")
        extra = ""
        if etype == "progress":
            extra = f" stage={event.get('stage')} status={event.get('status', '')}"
        elif etype == "token":
            extra = f" len={len(event.get('content', ''))}"
        elif etype == "component_progress":
            extra = f" component={event.get('component')} stage={event.get('stage')}"
        elif etype == "status":
            extra = f" content={event.get('content', '')[:80]}"
        async with self._lock:
            logger.debug(f"[EMIT] type={etype}{extra}  subscribers={len(self.subscribers)}")
            self.events.append(event)
            targets = [(qid, self._queues[qid]) for qid in self.subscribers if qid in self._queues]
        for _qid, q in targets:
            try:
                await q.put(event)
            except Exception:
                pass

    async def subscribe(self) -> tuple[list[dict], asyncio.Queue, int]:
        """Subscribe: returns (buffered_events, queue_for_new, subscription_id)."""
        async with self._lock:
            qid = self._next_id
            self._next_id += 1
            q: asyncio.Queue = asyncio.Queue()
            self._queues[qid] = q
            self.subscribers.add(qid)
            return list(self.events), q, qid

    async def unsubscribe(self, qid: int):
        """Remove subscriber."""
        async with self._lock:
            self.subscribers.discard(qid)
            self._queues.pop(qid, None)


# Active pipeline sessions by thread_id
active_sessions: dict[str, PipelineSession] = {}

HEARTBEAT_INTERVAL = 15  # seconds


async def run_pipeline(session: PipelineSession, user_message: str, thread_id: str):
    """Run ChatAgent, streaming chat tokens and assembly progress to session.

    V4: GraphInterrupt is caught inside chat_agent's assemble_ecoos_app tool.
    PRD review data arrives as a custom stream event ("prd_review").
    Resume happens when user sends prd_approve → new run_pipeline with resume message.
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}

        inputs = {"messages": [{"role": "user", "content": user_message}]}
        await session.emit({"type": "status", "content": "Обработка запроса..."})

        async for chunk in chat_agent.astream(
            inputs,
            config=config,
            stream_mode=["messages", "custom"],
        ):
            mode, data = chunk

            if mode == "messages":
                msg_chunk, metadata = data
                node = metadata.get("langgraph_node", "?")
                # Stream only agent responses (not tool messages)
                if hasattr(msg_chunk, "content") and msg_chunk.content:
                    if node == "agent":
                        await session.emit({
                            "type": "token",
                            "content": msg_chunk.content,
                        })
                    else:
                        logger.debug(f"[STREAM] skip message from node={node} len={len(msg_chunk.content)}")

            elif mode == "custom":
                # data = whatever tool's stream_writer() sent
                # Types: progress, result, prd_review, component_progress, status
                logger.debug(f"[STREAM] custom event: {json.dumps(data, ensure_ascii=False, default=str)[:200]}")
                await session.emit(data)

        await session.emit({"type": "done", "content": "Готово"})

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        await session.emit({"type": "error", "content": str(e)})

        await session.emit({"type": "done", "content": f"Ошибка: {e}"})

    finally:
        session.is_done = True


# ═══════════════════════════════════════════════════════════════════════════
# REST ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "v4"}


@app.get("/api/rag-status")
async def get_rag_status():
    """Check ChromaDB vector store status."""
    chroma_db_path = os.getenv("CHROMA_DB", "./chroma_db")
    rag_storage_path = os.getenv("RAG_STORAGE", "./rag_storage")

    chroma_exists = Path(chroma_db_path).exists() and any(Path(chroma_db_path).iterdir()) if Path(chroma_db_path).exists() else False
    rag_exists = Path(rag_storage_path).exists()

    source_files_count = 0
    if rag_exists:
        for ext in ['*.h', '*.hpp', '*.c', '*.cpp']:
            source_files_count += len(list(Path(rag_storage_path).rglob(ext)))

    return {
        "chroma_initialized": chroma_exists,
        "rag_storage_exists": rag_exists,
        "source_files_count": source_files_count,
        "chroma_path": chroma_db_path,
        "is_initializing": rag_init_status["running"],
        "init_progress": rag_init_status["progress"],
        "init_message": rag_init_status["message"],
    }


async def init_rag_generator() -> AsyncGenerator[str, None]:
    """Generator for streaming RAG init progress."""
    global rag_init_status

    rag_init_status = {"running": True, "progress": 0, "message": "Starting...", "error": None}

    try:
        yield f"data: {json.dumps({'progress': 0, 'message': 'Loading dependencies...'})}\n\n"
        await asyncio.sleep(0.1)

        rag_init_status["message"] = "Connecting to OpenRouter..."
        rag_init_status["progress"] = 5
        yield f"data: {json.dumps({'progress': 5, 'message': 'Connecting to OpenRouter embeddings API...'})}\n\n"

        from langchain_openai import OpenAIEmbeddings
        from langchain_community.document_loaders import DirectoryLoader, TextLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_chroma import Chroma

        RAG_STORAGE = os.getenv("RAG_STORAGE", "./rag_storage")
        CHROMA_DB = os.getenv("CHROMA_DB", "./chroma_db")
        EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "qwen/qwen3-embedding-8b")
        OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1")
        API_KEY = os.getenv("OPENAI_API_KEY")

        if not API_KEY:
            raise Exception("OPENAI_API_KEY not set in .env")

        if not Path(RAG_STORAGE).exists():
            raise Exception(f"RAG storage not found: {RAG_STORAGE}")

        rag_init_status["progress"] = 10
        yield f"data: {json.dumps({'progress': 10, 'message': f'Using OpenRouter model: {EMBEDDINGS_MODEL}'})}\n\n"

        embeddings = OpenAIEmbeddings(
            model=EMBEDDINGS_MODEL,
            openai_api_key=API_KEY,
            openai_api_base=OPENROUTER_URL,
        )

        rag_init_status["progress"] = 30
        rag_init_status["message"] = "Loading documents..."
        yield f"data: {json.dumps({'progress': 30, 'message': 'Loading documents from rag_storage...'})}\n\n"

        all_docs = []
        for ext in ['*.h', '*.hpp', '*.c', '*.cpp']:
            loader = DirectoryLoader(
                RAG_STORAGE,
                glob=f"**/{ext}",
                loader_cls=TextLoader,
                loader_kwargs={"encoding": "utf-8", "autodetect_encoding": True},
                recursive=True,
                silent_errors=True
            )
            docs = loader.load()
            all_docs.extend(docs)

        if not all_docs:
            raise Exception("No documents found in rag_storage")

        rag_init_status["progress"] = 50
        rag_init_status["message"] = f"Loaded {len(all_docs)} documents"
        yield f"data: {json.dumps({'progress': 50, 'message': f'Loaded {len(all_docs)} documents. Splitting into chunks...'})}\n\n"

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            separators=["\n\n", "typedef struct", "typedef enum", "interface ", "#define", "ECO_EXPORT", "\n"],
        )
        chunks = text_splitter.split_documents(all_docs)

        rag_init_status["progress"] = 60
        yield f"data: {json.dumps({'progress': 60, 'message': f'Created {len(chunks)} chunks. Adding metadata...'})}\n\n"

        for i, chunk in enumerate(chunks):
            source = chunk.metadata.get("source", "")
            if source:
                path_parts = Path(source).parts
                component = "unknown"
                for part in path_parts:
                    if "Eco." in part:
                        component = part
                        break
                file_name = Path(source).name
            else:
                component = "unknown"
                file_name = "unknown"

            chunk.metadata.update({
                "component": component,
                "file_name": file_name,
                "chunk_index": i,
            })

        rag_init_status["progress"] = 70
        yield f"data: {json.dumps({'progress': 70, 'message': f'Creating vector store with {len(chunks)} chunks...'})}\n\n"

        if Path(CHROMA_DB).exists():
            import shutil
            # Clear contents instead of rmtree — rmtree fails on Docker volume mounts
            for item in Path(CHROMA_DB).iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        rag_init_status["progress"] = 80
        yield f"data: {json.dumps({'progress': 80, 'message': 'Generating embeddings (this may take a while)...'})}\n\n"

        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=CHROMA_DB,
            collection_name="ecoos_components",
        )

        rag_init_status["progress"] = 100
        rag_init_status["message"] = "Complete!"
        rag_init_status["running"] = False
        yield f"data: {json.dumps({'progress': 100, 'message': f'Success! Indexed {len(chunks)} chunks.', 'done': True})}\n\n"

    except Exception as e:
        rag_init_status["error"] = str(e)
        rag_init_status["running"] = False
        yield f"data: {json.dumps({'progress': -1, 'message': f'Error: {str(e)}', 'error': True})}\n\n"


@app.get("/api/init-rag")
async def init_rag():
    """Start RAG initialization with progress via SSE."""
    global rag_init_status

    if rag_init_status["running"]:
        raise HTTPException(status_code=409, detail="RAG initialization already in progress")

    return StreamingResponse(
        init_rag_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ═══════════════════════════════════════════════════════════════════════════
# WEBSOCKET — subscriber to pipeline events + heartbeat
# ═══════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/chat/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await websocket.accept()
    logger.info(f"Client #{thread_id} connected")

    sub_id: int | None = None
    session: PipelineSession | None = None
    hb_task: asyncio.Task | None = None

    async def heartbeat():
        """Send heartbeat every HEARTBEAT_INTERVAL seconds to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await websocket.send_json({"type": "heartbeat"})
        except Exception:
            pass  # Connection closed, stop silently

    try:
        while True:
            # Check if there's an existing pipeline session for this thread
            session = active_sessions.get(thread_id)

            if session and not session.is_done:
                # Pipeline already running — resume streaming
                buffered, queue, sub_id = await session.subscribe()

                # Replay buffered events
                logger.info(f"[WS] Replaying {len(buffered)} buffered events for #{thread_id}")
                for event in buffered:
                    logger.debug(f"[WS→CLIENT replay] type={event.get('type', '?')}")
                    await websocket.send_json(event)

                # Start heartbeat
                hb_task = asyncio.create_task(heartbeat())

                # Stream new events until done
                while True:
                    event = await queue.get()
                    await websocket.send_json(event)
                    if event.get("type") == "done":
                        break

                await session.unsubscribe(sub_id)
                sub_id = None
                if hb_task:
                    hb_task.cancel()
                    hb_task = None

            else:
                # No active pipeline — wait for client message
                data = await websocket.receive_text()
                request = json.loads(data)
                logger.info(f"[WS←CLIENT] thread={thread_id} type={request.get('type', 'message')} msg={str(request.get('message', ''))[:80]}")

                # V4: handle PRD approval/rejection from frontend
                # Convert to a user message that tells the chat agent to call resume_assembly
                if request.get("type") == "prd_approve":
                    prd = request.get("prd", {})
                    arch_thread = request.get("architect_thread_id", "")
                    prd_json = json.dumps(prd, ensure_ascii=False) if prd else ""
                    user_message = (
                        f"User approved the PRD. Call resume_assembly with "
                        f"architect_thread_id=\"{arch_thread}\", approved=true"
                        + (f", modified_prd_json='{prd_json}'" if prd_json else "")
                    )
                elif request.get("type") == "prd_reject":
                    arch_thread = request.get("architect_thread_id", "")
                    user_message = (
                        f"User rejected the PRD. Call resume_assembly with "
                        f"architect_thread_id=\"{arch_thread}\", approved=false"
                    )
                else:
                    user_message = request.get("message")
                if not user_message:
                    continue

                # Create new pipeline session
                session = PipelineSession()
                active_sessions[thread_id] = session

                # Subscribe BEFORE starting pipeline (don't miss early events)
                buffered, queue, sub_id = await session.subscribe()

                # Start pipeline in background
                session.task = asyncio.create_task(
                    run_pipeline(session, user_message, thread_id)
                )

                # Start heartbeat
                hb_task = asyncio.create_task(heartbeat())

                # Stream events until done
                while True:
                    event = await queue.get()
                    etype = event.get("type", "?")
                    logger.debug(f"[WS→CLIENT] type={etype} thread={thread_id}")
                    await websocket.send_json(event)
                    if etype == "done":
                        break

                await session.unsubscribe(sub_id)
                sub_id = None
                if hb_task:
                    hb_task.cancel()
                    hb_task = None

    except WebSocketDisconnect:
        logger.info(f"Client #{thread_id} disconnected")
    except Exception as e:
        logger.exception(f"WebSocket error for #{thread_id}: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
    finally:
        # Cleanup subscription but NOT the pipeline
        if session and sub_id is not None:
            try:
                await session.unsubscribe(sub_id)
            except Exception:
                pass
        if hb_task:
            hb_task.cancel()
        logger.info(f"Client #{thread_id} cleanup done (pipeline continues if running)")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
