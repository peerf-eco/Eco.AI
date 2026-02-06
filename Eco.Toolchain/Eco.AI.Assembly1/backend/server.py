import os
import sys
import json
import asyncio
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH для импорта agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict, Any, AsyncGenerator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

# Импортируем наш агент
from agent.graph import create_agent_graph, create_simple_graph
from agent.main import get_llm

load_dotenv()

# Глобальная переменная для отслеживания статуса инициализации RAG
rag_init_status = {"running": False, "progress": 0, "message": "", "error": None}

app = FastAPI(title="EcoOS Agent API")

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на реальный домен фронта
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтируем папку с выходными файлами, чтобы можно было их скачивать
os.makedirs("output", exist_ok=True)
app.mount("/files", StaticFiles(directory="output"), name="files")

# Инициализация графа
# Используем MemorySaver внутри графа, поэтому создаем его один раз
# В продакшене лучше использовать PostgresSaver
llm = get_llm()
graph = create_agent_graph(llm)

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"

@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/rag-status")
async def get_rag_status():
    """Проверяет статус векторного хранилища ChromaDB"""
    chroma_db_path = os.getenv("CHROMA_DB", "./chroma_db")
    rag_storage_path = os.getenv("RAG_STORAGE", "./rag_storage")
    
    chroma_exists = Path(chroma_db_path).exists() and any(Path(chroma_db_path).iterdir()) if Path(chroma_db_path).exists() else False
    rag_exists = Path(rag_storage_path).exists()
    
    # Подсчитываем файлы в rag_storage
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
    """Генератор для стриминга прогресса инициализации RAG"""
    global rag_init_status
    
    rag_init_status = {"running": True, "progress": 0, "message": "Starting...", "error": None}
    
    try:
        yield f"data: {json.dumps({'progress': 0, 'message': 'Loading dependencies...'})}\n\n"
        await asyncio.sleep(0.1)
        
        # Импортируем зависимости
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
        
        # Проверка rag_storage
        if not Path(RAG_STORAGE).exists():
            raise Exception(f"RAG storage not found: {RAG_STORAGE}")
        
        rag_init_status["progress"] = 10
        yield f"data: {json.dumps({'progress': 10, 'message': f'Using OpenRouter model: {EMBEDDINGS_MODEL}'})}\n\n"
        
        # Инициализация эмбеддингов через OpenRouter API
        embeddings = OpenAIEmbeddings(
            model=EMBEDDINGS_MODEL,
            openai_api_key=API_KEY,
            openai_api_base=OPENROUTER_URL,
        )
        
        rag_init_status["progress"] = 30
        rag_init_status["message"] = "Loading documents..."
        yield f"data: {json.dumps({'progress': 30, 'message': 'Loading documents from rag_storage...'})}\n\n"
        
        # Загрузка документов
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
        
        # Чанкинг
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            separators=["\n\n", "typedef struct", "typedef enum", "interface ", "#define", "ECO_EXPORT", "\n"],
        )
        chunks = text_splitter.split_documents(all_docs)
        
        rag_init_status["progress"] = 60
        yield f"data: {json.dumps({'progress': 60, 'message': f'Created {len(chunks)} chunks. Adding metadata...'})}\n\n"
        
        # Метаданные
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
        
        # Удаляем старую базу
        if Path(CHROMA_DB).exists():
            import shutil
            shutil.rmtree(CHROMA_DB)
        
        rag_init_status["progress"] = 80
        yield f"data: {json.dumps({'progress': 80, 'message': 'Generating embeddings (this may take a while)...'})}\n\n"
        
        # Создание векторного хранилища
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
    """Запускает инициализацию RAG с прогрессом через SSE"""
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

@app.websocket("/ws/chat/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await websocket.accept()
    
    try:
        while True:
            # 1. Получаем сообщение от клиента
            data = await websocket.receive_text()
            request = json.loads(data)
            user_message = request.get("message")
            
            if not user_message:
                continue
                
            # 2. Подготовка конфига для графа
            config = {"configurable": {"thread_id": thread_id}}
            
            # Начальное состояние (добавляем сообщение пользователя)
            # Важно: LangGraph сам добавит сообщение в историю, если передать его в инпуте
            inputs = {
                "messages": [HumanMessage(content=user_message)],
                # Остальные поля инициализируются дефолтами в графе или сохраняются из памяти
            }

            # 3. Стриминг событий графа
            # stream_mode="updates" возвращает обновления состояния после каждого узла
            # stream_mode="messages" возвращает токены (если поддерживается)
            
            await websocket.send_json({
                "type": "status",
                "content": "Analysing request..."
            })
            
            # Используем astream_events для детального контроля
            async for event in graph.astream_events(inputs, config=config, version="v1"):
                kind = event["event"]
                
                # События начала/конца узлов (для прогресс-бара)
                if kind == "on_chain_start":
                    node_name = event["name"]
                    if node_name in ["analyze_request", "select_components", "retrieve_context", "generate_code", "review_code"]:
                        await websocket.send_json({
                            "type": "progress",
                            "stage": node_name,
                            "status": "running"
                        })
                
                elif kind == "on_chain_end":
                    node_name = event["name"]
                    if node_name in ["analyze_request", "select_components", "retrieve_context", "generate_code", "review_code"]:
                         await websocket.send_json({
                            "type": "progress",
                            "stage": node_name,
                            "status": "completed"
                        })

                # Стриминг токенов от LLM (для чата)
                elif kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        await websocket.send_json({
                            "type": "token",
                            "content": content
                        })
            
            # 4. Финальный ответ (состояние)
            # Получаем последнее состояние, чтобы узнать результат
            final_state = await graph.aget_state(config)
            generated_files = final_state.values.get("generated_files", [])
            
            # Отправляем список сгенерированных файлов
            if generated_files:
                files_info = []
                for f in generated_files:
                    files_info.append({
                        "path": f["path"],
                        "type": f["file_type"],
                        "url": f"/files/{f['path']}"
                    })
                
                await websocket.send_json({
                    "type": "files",
                    "files": files_info
                })
                
            await websocket.send_json({
                "type": "done",
                "content": "Generation complete"
            })

    except WebSocketDisconnect:
        print(f"Client #{thread_id} disconnected")
    except Exception as e:
        print(f"Error: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

