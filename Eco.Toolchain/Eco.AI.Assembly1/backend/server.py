import os
import sys
import json
import uuid
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


# ═══════════════════════════════════════════════════════════════════════════
# V5 WEBSOCKET — three-node pipeline (planner → coder → executor)
# ═══════════════════════════════════════════════════════════════════════════

from agent.chat_agent import create_chat_agent_v5, make_chat_agent_initial_state


@app.websocket("/ws/v5/chat")
async def v5_chat_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Build LLM (mirrors agent/main.py:get_llm pattern)
    try:
        from agent.main import get_llm as _get_llm
        llm = _get_llm()
    except Exception:
        # Fallback if agent.main.get_llm not importable as a function
        llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "z-ai/glm-5.1"),
            temperature=0,
            openai_api_key=os.environ["OPENAI_API_KEY"],
            openai_api_base=os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
            timeout=120,
            max_retries=1,
        )

    graph = create_chat_agent_v5(llm)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 100}
    logger.info(f"[V5 WS] connected thread_id={thread_id}")

    # Send heartbeat so frontend confirms the V5 endpoint is alive.
    await websocket.send_json({"type": "heartbeat", "version": "v5"})

    state = None
    try:
        while True:
            raw = await websocket.receive_text()
            logger.info(f"[V5 WS] recv raw={raw[:200]}")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            # Accept both keys — frontend uses "message", spec uses "content".
            user_msg = payload.get("content") or payload.get("message") or ""
            if not user_msg:
                # PRD-approve / PRD-reject coming from V4 UI? Just ignore — V5 has no PRD-modal.
                if payload.get("type") in ("prd_approve", "prd_reject"):
                    logger.info(f"[V5 WS] ignored V4-style {payload.get('type')} (V5 uses inline approve)")
                    continue
                await websocket.send_json({"type": "error", "content": f"Missing 'message'/'content' field in payload: {raw[:100]}"})
                continue

            if state is None:
                state = make_chat_agent_initial_state(user_msg, max_iterations=5)
            else:
                state["planner_messages"] = state.get("planner_messages", []) + [
                    {"role": "user", "content": user_msg}
                ]

            try:
                async for kind, data in graph.astream(state, config, stream_mode=["updates", "custom"]):
                    if kind == "updates":
                        for node, update in data.items():
                            if isinstance(update, dict) and "phase" in update:
                                await websocket.send_json({"type": "phase_change", "phase": update["phase"]})
                            if node == "planner" and isinstance(update, dict) and "planner_messages" in update:
                                for m in update["planner_messages"]:
                                    # Only forward the LLM's user-facing narration.
                                    # Skip ToolMessage (raw tool output — clutters chat with header dumps etc.).
                                    msg_class = type(m).__name__
                                    if msg_class in ("ToolMessage", "HumanMessage"):
                                        continue
                                    content = getattr(m, "content", "") or ""
                                    if not isinstance(content, str):
                                        # Some LLMs return content as a list of blocks; flatten to text.
                                        try:
                                            content = "".join(b.get("text", "") for b in content if isinstance(b, dict))
                                        except Exception:
                                            content = str(content)
                                    if content.strip():
                                        await websocket.send_json({"type": "planner_message", "content": content})
                            elif node == "coder":
                                # Send a human-readable progress line instead of raw dict.
                                summary = update.get("coder_summary_md") if isinstance(update, dict) else None
                                if summary:
                                    await websocket.send_json({"type": "coder_progress", "data": f"Coder finished. Summary:\n\n{summary[:1500]}"})
                                else:
                                    # Stream individual coder AIMessages (file-write announcements, reasoning).
                                    for m in (update.get("coder_messages", []) if isinstance(update, dict) else []):
                                        if type(m).__name__ in ("ToolMessage", "HumanMessage"):
                                            continue
                                        content = getattr(m, "content", "") or ""
                                        if isinstance(content, list):
                                            content = "".join(b.get("text", "") for b in content if isinstance(b, dict))
                                        if content.strip():
                                            await websocket.send_json({"type": "coder_progress", "data": content[:1500]})
                            elif node == "executor":
                                fb = update.get("feedback_md") if isinstance(update, dict) else None
                                exec_summary = update.get("executor_summary_md") if isinstance(update, dict) else None
                                if exec_summary:
                                    await websocket.send_json({"type": "executor_progress", "data": f"✓ Build & tests succeeded:\n\n{exec_summary[:1500]}"})
                                elif fb:
                                    await websocket.send_json({"type": "executor_progress", "data": f"✗ Build/test failed, returning to coder:\n\n{fb[:1500]}"})
                                else:
                                    for m in (update.get("executor_messages", []) if isinstance(update, dict) else []):
                                        if type(m).__name__ in ("ToolMessage", "HumanMessage"):
                                            continue
                                        content = getattr(m, "content", "") or ""
                                        if isinstance(content, list):
                                            content = "".join(b.get("text", "") for b in content if isinstance(b, dict))
                                        if content.strip():
                                            await websocket.send_json({"type": "executor_progress", "data": content[:1500]})
                    elif kind == "custom":
                        await websocket.send_json(data)
            except Exception as e:
                logger.exception(f"[V5 WS] graph error thread_id={thread_id}")
                await websocket.send_json({"type": "error", "content": f"Graph error: {type(e).__name__}: {e}"})
                continue

            # Refresh state from checkpointer
            try:
                state = graph.get_state(config).values
            except Exception:
                pass

            if state and state.get("phase") == "done":
                await websocket.send_json({
                    "type": "final_result",
                    "status": state.get("last_status", ""),
                    "summary": state.get("executor_summary_md", "") or state.get("coder_summary_md", ""),
                })
                break

    except WebSocketDisconnect:
        logger.info(f"[V5 WS] client disconnected thread_id={thread_id}")
    except Exception:
        logger.exception(f"[V5 WS] handler crashed thread_id={thread_id}")
        try:
            await websocket.close()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# V6 WEBSOCKET — five-node pipeline (planner → plan_gate → setup → coder → builder → tester)
# Spec: docs/superpowers/specs/2026-05-13-v6-pipeline-design.md §9
#
# Client → server messages:
#   {"type": "user_request", "user_request": "...", "project_dir"?: "...", "max_retries"?: 3}
#   {"type": "plan_decision", "approved": true|false, "modified_plan_md"?: "...", "reason"?: "..."}
#   {"type": "escalation_decision", "continue": true|false}
#   {"type": "abort"}
#
# Server → client events:
#   {"type": "heartbeat", "version": "v6", "thread_id": "..."}
#   {"type": "phase_change", "phase": "...", "node": "..."}
#   {"type": "node_done", "node": "planner|setup|coder|builder|tester", ...}
#   {"type": "build_fail", "error_md": "...", "retry_count": N}
#   {"type": "test_fail", "reason_md": "...", "retry_count": N}
#   {"type": "plan_review_required", "plan_md": "...", "components": [...], "project_name": "..."}
#   {"type": "escalation_required", "reason": "...", "failure_origin": "...", "retry_count": N, "max_retries": M, "build_log": "...", ...}
#   {"type": "pipeline_done", "status": "success|user_aborted|...", "build_artifact"?, "tester_report_md"?}
#   {"type": "error", "content": "..."}
# ═══════════════════════════════════════════════════════════════════════════

# V6 checkpointer is shared across reconnects so that a client that sends
# ?thread_id=<existing> can resume a paused graph after page reload.
_v6_checkpointer = None


def _get_v6_checkpointer():
    global _v6_checkpointer
    if _v6_checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver
        _v6_checkpointer = MemorySaver()
    return _v6_checkpointer


@app.websocket("/ws/v6/chat")
async def v6_chat_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Lazy imports — keeps startup light if V6 layer is in flux.
    from agent.v6.graph import create_v6_graph
    from agent.v6.state import make_initial_v6_state
    from langgraph.types import Command

    try:
        from agent.main import get_llm as _get_llm
        llm = _get_llm()
    except Exception:
        llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "moonshotai/kimi-k2-thinking"),
            temperature=0,
            openai_api_key=os.environ["OPENAI_API_KEY"],
            openai_api_base=os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
            timeout=30,
            max_retries=2,
        )

    # Platform-dependent toolchain defaults. Override any via env.
    _is_windows = sys.platform == "win32"
    sdk_root  = Path(os.getenv("V6_SDK_ROOT", "source"))
    if _is_windows:
        cli_path: Path | None = Path(os.getenv("V6_CLI_PATH", "eco.sli/eco-cli.exe"))
        vcvarsall: Path | None = Path(os.getenv("V6_VCVARSALL",
            r"C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvarsall.bat"))
        make_exe = Path(os.getenv("V6_MAKE_EXE", r"C:/Users/gaevy/gcc/bin/make.exe"))
    else:
        # Linux/macOS: eco-cli.exe is Windows-only but we run it through
        # Wine (see Dockerfile + V6_CLI_PREFIX in tools/setup.py). If env
        # didn't set V6_CLI_PATH, we have no CLI and pull falls back to
        # the local sdk_root mirror — kept as a safety net only.
        cli_path = Path(os.environ["V6_CLI_PATH"]) if os.getenv("V6_CLI_PATH") else None
        vcvarsall = None
        make_exe = Path(os.getenv("V6_MAKE_EXE", "make"))

    graph = create_v6_graph(
        llm,
        sdk_root=sdk_root,
        cli_path=cli_path,
        vcvarsall=vcvarsall,
        make_exe=make_exe,
        checkpointer=_get_v6_checkpointer(),
    )

    # Allow client to resume an existing thread via ?thread_id=<uuid>. If
    # absent or empty, generate a fresh one. The shared checkpointer keeps
    # paused graph state between reconnects.
    requested_tid = websocket.query_params.get("thread_id", "").strip()
    thread_id = requested_tid or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 200}
    logger.info(f"[V6 WS] connected thread_id={thread_id} (resumed={bool(requested_tid)})")
    await websocket.send_json({"type": "heartbeat", "version": "v6", "thread_id": thread_id})

    # On resume: replay current pending interrupts so client UI can re-render.
    try:
        snapshot = graph.get_state(config)
        if snapshot.next:
            for task in snapshot.tasks:
                for interrupt_obj in (task.interrupts or ()):
                    value = interrupt_obj.value or {}
                    if task.name == "plan_gate":
                        await websocket.send_json({
                            "type": "plan_review_required",
                            "plan_md":      value.get("plan_md", ""),
                            "components":   value.get("components", []),
                            "project_name": value.get("project_name", ""),
                        })
                    elif task.name == "escalate":
                        await websocket.send_json({
                            "type": "escalation_required",
                            "reason":           value.get("reason", "unknown"),
                            "failure_origin":   value.get("failure_origin", ""),
                            "retry_count":      value.get("retry_count", 0),
                            "max_retries":      value.get("max_retries", 3),
                            "build_log":        value.get("build_log", "")[:4000],
                            "tester_report_md": value.get("tester_report_md", "")[:4000],
                            "plan_md":          value.get("plan_md", ""),
                            "coder_summary_md": value.get("coder_summary_md", "")[:2000],
                        })
    except Exception:
        logger.exception(f"[V6 WS] resume replay failed thread_id={thread_id}")

    last_phase: str | None = None

    async def emit_updates(updates_dict: dict):
        """Translate a LangGraph node update into typed WS events."""
        nonlocal last_phase
        for node, update in updates_dict.items():
            if not isinstance(update, dict):
                continue
            phase = update.get("phase")
            if phase and phase != last_phase:
                await websocket.send_json({"type": "phase_change", "phase": phase, "node": node})
                last_phase = phase
            if node == "planner" and "plan_md" in update:
                await websocket.send_json({
                    "type": "node_done", "node": "planner",
                    "project_name": update.get("project_name", ""),
                    "components_count": len(update.get("components", [])),
                })
            elif node == "setup" and "downloaded_paths" in update:
                await websocket.send_json({
                    "type": "node_done", "node": "setup",
                    "downloaded_paths": update["downloaded_paths"],
                })
            elif node == "coder" and "coder_summary_md" in update:
                await websocket.send_json({
                    "type": "node_done", "node": "coder",
                    "summary_md": update["coder_summary_md"][:2000],
                })
            elif node == "builder":
                if "build_artifact" in update:
                    await websocket.send_json({
                        "type": "node_done", "node": "builder",
                        "build_artifact": update["build_artifact"],
                    })
                elif "build_log" in update:
                    await websocket.send_json({
                        "type": "build_fail",
                        "error_md": update["build_log"][:4000],
                        "retry_count": update.get("retry_count", 0),
                    })
            elif node == "tester":
                if update.get("last_status") == "success":
                    await websocket.send_json({
                        "type": "node_done", "node": "tester",
                        "reason_md": update.get("tester_report_md", "")[:2000],
                    })
                elif "tester_report_md" in update:
                    await websocket.send_json({
                        "type": "test_fail",
                        "reason_md": update["tester_report_md"][:4000],
                        "retry_count": update.get("retry_count", 0),
                    })

    async def handle_pending_interrupts() -> bool:
        """If the graph paused on an interrupt, emit the matching event.

        Returns True if an interrupt was emitted (client should respond),
        False if the run reached END.
        """
        snapshot = graph.get_state(config)
        pending_nodes = snapshot.next or ()
        if not pending_nodes:
            return False
        for task in snapshot.tasks:
            for interrupt_obj in (task.interrupts or ()):
                value = interrupt_obj.value or {}
                if task.name == "plan_gate":
                    await websocket.send_json({
                        "type": "plan_review_required",
                        "plan_md":      value.get("plan_md", ""),
                        "components":   value.get("components", []),
                        "project_name": value.get("project_name", ""),
                    })
                elif task.name == "escalate":
                    await websocket.send_json({
                        "type": "escalation_required",
                        "reason":           value.get("reason", "unknown"),
                        "failure_origin":   value.get("failure_origin", ""),
                        "retry_count":      value.get("retry_count", 0),
                        "max_retries":      value.get("max_retries", 3),
                        "build_log":        value.get("build_log", "")[:4000],
                        "tester_report_md": value.get("tester_report_md", "")[:4000],
                        "plan_md":          value.get("plan_md", ""),
                        "coder_summary_md": value.get("coder_summary_md", "")[:2000],
                    })
        return True

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            msg_type = payload.get("type", "user_request")

            if msg_type == "abort":
                await websocket.send_json({"type": "pipeline_done", "status": "user_aborted"})
                break
            elif msg_type == "plan_decision":
                resume_val = {"approved": bool(payload.get("approved", False))}
                if payload.get("modified_plan_md"):
                    resume_val["modified_plan_md"] = payload["modified_plan_md"]
                if payload.get("reason"):
                    resume_val["reason"] = payload["reason"]
                graph_input = Command(resume=resume_val)
            elif msg_type == "escalation_decision":
                graph_input = Command(resume={"continue": bool(payload.get("continue", False))})
            else:  # user_request (also accepts plain "message"/"content" for compat)
                user_req = (payload.get("user_request")
                            or payload.get("message")
                            or payload.get("content") or "")
                if not user_req:
                    await websocket.send_json({"type": "error", "content": "Missing user_request"})
                    continue
                initial = make_initial_v6_state(
                    user_req,
                    max_retries=int(payload.get("max_retries", 3)),
                    target_os=str(payload.get("target_os") or "Linux"),
                    target_arch=str(payload.get("target_arch") or "x86_64"),
                )
                if payload.get("project_dir"):
                    initial["project_dir"] = payload["project_dir"]
                graph_input = initial

            try:
                async for kind, data in graph.astream(
                    graph_input, config=config, stream_mode=["updates", "custom"]
                ):
                    if kind == "updates":
                        await emit_updates(data)
                    elif kind == "custom":
                        await websocket.send_json(data)
            except Exception as e:
                logger.exception(f"[V6 WS] graph error thread_id={thread_id}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"Graph error: {type(e).__name__}: {e}",
                })
                continue

            if await handle_pending_interrupts():
                # Wait for client decision in next loop iteration.
                continue

            snapshot_values = graph.get_state(config).values
            await websocket.send_json({
                "type": "pipeline_done",
                "status":           snapshot_values.get("last_status", "unknown"),
                "build_artifact":   snapshot_values.get("build_artifact", ""),
                "tester_report_md": snapshot_values.get("tester_report_md", ""),
            })
            break

    except WebSocketDisconnect:
        logger.info(f"[V6 WS] disconnected thread_id={thread_id}")
    except Exception:
        logger.exception(f"[V6 WS] handler crashed thread_id={thread_id}")
        try:
            await websocket.close()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# V7 WEBSOCKET — three-agent pipeline (architect → coder → tester) with
# backward handoff edges. No LangGraph, no checkpointer, no HITL interrupts.
#
# Reuses the v6 client event shape so the existing frontend (use-v6-socket.ts)
# can render v7 with no changes beyond the WS URL — see frontend env flag
# NEXT_PUBLIC_PIPELINE_VERSION=v7.
#
# Mapping (v7 internal → v6 client event):
#   architect-agent active   → phase_change phase=planning node=planner
#   coder-agent active       → phase_change phase=coding   node=coder
#   tester-agent active      → phase_change phase=testing  node=tester
#   EcoAgent.TEXT_DELTA      → node_event event=text_delta
#   EcoAgent.THINKING_DELTA  → node_event event=thinking_delta
#   EcoAgent.TOOL_START/END  → node_event event=tool_call_start|end
#   orchestrator terminates  → pipeline_done status=success|failed
#
# Note: v7 has no plan_gate or escalate, so plan_review_required and
# escalation_required events are NEVER emitted. The frontend already tolerates
# their absence (use-v6-socket.ts only renders them on receipt).
# ═══════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/v7/chat")
async def v7_chat_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Lazy imports — keep startup light even if v7 layer churns.
    from agent.v6.entry import build_v7_pipeline
    from agent.v6.eco_agent import EventType

    # V7 uses pi_ai.Model directly (no langchain). This is the path where
    # delta.reasoning is preserved end-to-end through to the UI thinking blocks.
    from agent.main import get_model as _get_model
    model = _get_model()

    is_windows = sys.platform == "win32"
    cli_path: Path | None = (
        Path(os.environ["V6_CLI_PATH"]) if os.getenv("V6_CLI_PATH") else None
    )
    make_exe = Path(os.getenv(
        "V6_MAKE_EXE",
        r"C:/Users/gaevy/gcc/bin/make.exe" if is_windows else "make",
    ))

    thread_id = str(uuid.uuid4())
    project_dir = Path(os.getenv("V7_OUTPUT_ROOT", "./output")) / f"v7-{thread_id[:8]}"
    project_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"[V7 WS] connected thread_id={thread_id} project_dir={project_dir}")
    await websocket.send_json({"type": "heartbeat", "version": "v7", "thread_id": thread_id})

    # v6 client expects these agent identifiers in its `node` field — translate.
    PHASE_OF = {"architect": "planning", "coder": "coding",  "tester": "testing"}
    NODE_OF  = {"architect": "planner",  "coder": "coder",   "tester": "tester"}

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            msg_type = payload.get("type", "user_request")
            if msg_type == "abort":
                # v7 orchestrator.run is sync inside to_thread — we can't cancel
                # mid-run. Surface as a clean done so the UI unfreezes.
                await websocket.send_json({"type": "pipeline_done", "status": "user_aborted"})
                break
            if msg_type in ("plan_decision", "escalation_decision"):
                # v7 has no HITL interrupts — silently ignore these v6 leftovers
                # if the frontend sends them by mistake.
                continue

            user_req = (
                payload.get("user_request")
                or payload.get("message")
                or payload.get("content")
                or ""
            )
            if not user_req:
                await websocket.send_json({"type": "error", "content": "Missing user_request"})
                continue

            # ── Event bridge: sync on_event (called from to_thread worker) →
            #    asyncio.Queue → main loop sends through WebSocket.
            loop = asyncio.get_event_loop()
            ev_queue: asyncio.Queue = asyncio.Queue()
            SENTINEL = object()

            def on_event(wrapped: dict):
                # wrapped = {"agent": "architect|coder|tester", "event": EcoAgentEvent}
                # Runs in the worker thread spawned by asyncio.to_thread.
                try:
                    loop.call_soon_threadsafe(ev_queue.put_nowait, wrapped)
                except RuntimeError:
                    pass  # loop closed, drop event silently

            orch = build_v7_pipeline(
                model=model,
                cli_path=cli_path,
                project_dir=project_dir,
                make_exe=make_exe,
                on_event=on_event,
            )

            async def run_orchestrator():
                try:
                    return await asyncio.to_thread(orch.run, user_req)
                finally:
                    loop.call_soon_threadsafe(ev_queue.put_nowait, SENTINEL)

            async def drain_events():
                current_agent: str | None = None
                while True:
                    item = await ev_queue.get()
                    if item is SENTINEL:
                        return
                    agent = item.get("agent")
                    ev = item.get("event")
                    if agent is None or ev is None:
                        continue
                    if agent != current_agent:
                        current_agent = agent
                        await websocket.send_json({
                            "type":  "phase_change",
                            "phase": PHASE_OF.get(agent, "planning"),
                            "node":  NODE_OF.get(agent, "planner"),
                        })
                    etype = ev.type.value if hasattr(ev.type, "value") else str(ev.type)
                    if etype in ("text_delta", "thinking_delta",
                                 "tool_call_start", "tool_call_end"):
                        await websocket.send_json({
                            "type":  "node_event",
                            "node":  NODE_OF.get(agent, "planner"),
                            "event": etype,
                            "data":  ev.data or {},
                        })
                    # Other EcoAgent events (start/iteration/done/error/etc) are
                    # bookkeeping — orchestrator-level done is emitted below.

            try:
                run_task = asyncio.create_task(run_orchestrator())
                drain_task = asyncio.create_task(drain_events())
                result, _ = await asyncio.gather(run_task, drain_task)
            except Exception as e:
                logger.exception(f"[V7 WS] orchestrator crashed thread_id={thread_id}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"Orchestrator error: {type(e).__name__}: {e}",
                })
                break

            # Translate OrchestratorResult into v6-shape pipeline_done.
            #   terminal + edge=done → success
            #   terminal + edge=fail → failed (with last_message as reason)
            #   anything else        → failed (loop_exceeded / agent_failed / unknown_edge)
            success = (result.status == "terminal" and result.terminal_edge == "done")
            await websocket.send_json({
                "type":             "pipeline_done",
                "status":           "success" if success else "failed",
                "build_artifact":   "",
                "tester_report_md": result.last_message
                                    + (f"\n\n(orchestrator: {result.status}"
                                       + (f", edge={result.terminal_edge}"
                                          if result.terminal_edge else "")
                                       + f", hops={len(result.hops)})"),
            })
            break

    except WebSocketDisconnect:
        logger.info(f"[V7 WS] disconnected thread_id={thread_id}")
    except Exception:
        logger.exception(f"[V7 WS] handler crashed thread_id={thread_id}")
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
