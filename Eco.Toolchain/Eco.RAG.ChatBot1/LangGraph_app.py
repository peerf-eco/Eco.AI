import os
import re
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
import weaviate
from weaviate.classes.query import MetadataQuery
from weaviate.classes.query import Filter
import logging
from dotenv import load_dotenv
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from typing import Any


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # You can set the level to INFO, WARNING, etc., as needed.
# Create a logger
logger = logging.getLogger(__name__)

# Функция извлечения интерфейса
def extract_interface(query: str) -> str | None:
    match = re.search(r"\bI[A-Za-z0-9_]+\b", query)
    return match.group(0) if match else None

# Import streamlit (missing import statement)
import streamlit as st

class RAGState(TypedDict):
    question: str
    documents: List[Document]
    context: str
    answer: str
    sources: List[dict]
    llm: Any
    search_alpha: float

# Configure Streamlit page
st.set_page_config(
    page_title="RAG Chat with OpenRouter & Weaviate",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 RAG Chat Application")
st.markdown("*Powered by OpenRouter API and Weaviate Vector Database*")

# Initialize session state variables properly
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processed" not in st.session_state:
    st.session_state.processed = {}

openrouter_api_key = None
yandex_api_key = None
yandex_folder_id = None


# Initialize embedding model
@st.cache_resource
def load_embedding_model():
    """Load and cache the embedding model"""
    return HuggingFaceEmbeddings(
        model_name=os.getenv("EMBEDDING_MODEL"),
        model_kwargs={'device': 'cpu'}
    )


# Rerank
@st.cache_resource
def load_reranker():
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

reranker = load_reranker()

def load_llm(provider: str, model: str, **kwargs):
    try:
        if provider == "Yandex Cloud":
            from langchain_community.llms import YandexGPT

            api_key = kwargs.get("api_key")
            folder_id = kwargs.get("folder_id")

            if not api_key or not folder_id:
                st.error("❌ Yandex Cloud API key or Folder ID is missing")
                return None

            # YandexGPT читает ТОЛЬКО environment variables
            os.environ["YC_API_KEY"] = api_key
            os.environ["YC_FOLDER_ID"] = folder_id

            return YandexGPT(
                model_name=model,
                temperature=0.1,
                max_tokens=2000
            )

        elif provider == "OpenRouter":
            api_key = kwargs.get("api_key")

            if not api_key:
                st.error("❌ OpenRouter API key is missing")
                return None

            return ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.1,
                max_tokens=2000
            )

    except Exception as e:
        st.error(f"Error initializing {provider} LLM: {e}")
        return None


# Weaviate connection and query functions
def connect_to_weaviate(url):
    """Connect to Weaviate instance"""
    try:
        if url.startswith("http://localhost") or url.startswith("http://127.0.0.1"):
            client = weaviate.connect_to_local(host=url.split("://")[1].split(":")[0])
        else:
            client = weaviate.connect_to_custom(
                http_host=url.split("://")[1].split(":")[0],
                http_port=int(url.split(":")[-1]) if ":" in url.split("://")[1] else 80,
                http_secure=url.startswith("https")
            )
        return client
    except Exception as e:
        st.error(f"Failed to connect to Weaviate: {e}")
        return None

def get_collections_list(url):
    """Get list of all collections from Weaviate"""
    client = None
    try:
        client = connect_to_weaviate(url)
        if not client:
            return []

        collections = client.collections.list_all()

        # В weaviate-client 4.x это уже список строк
        return list(collections)

    except Exception as e:
        st.error(f"Error fetching collections: {e}")
        return []

    finally:
        if client:
            client.close()

def search_single_collection(
    client,
    collection_name: str,
    query_text: str,
    query_vector: list,
    limit: int,
    alpha: float
):
    """Search in a single Weaviate collection"""

    if not client.collections.exists(collection_name):
        return []

    collection = client.collections.get(collection_name)

    # Filters
    interface = extract_interface(query_text)

    filters = None
    # if interface:
    #     filters = Filter.by_property("interface").equal(interface)

    # Search
    response = collection.query.hybrid(
        query=query_text,
        vector=query_vector,
        alpha=alpha,
        limit=limit,
        filters=filters,  # 🔥 ВОТ СЮДА
        return_metadata=MetadataQuery(distance=True)
    )

    if not response:
        print("Weaviate returned None")
        return []

    if not response.objects:
        print("No objects found")
        return []

    results = []

    for obj in response.objects:

        content = obj.properties.get("content") or ""
        title = obj.properties.get("title") or "Unknown"

        distance = 1.0
        if hasattr(obj.metadata, "distance") and obj.metadata.distance is not None:
            distance = float(obj.metadata.distance)

        doc = Document(
            page_content=str(content),
            metadata={
                **obj.properties,
                "distance": distance,
                "collection": collection_name
            }
        )

        results.append(doc)

    return results


def query_weaviate(
    query_text: str,
    weaviate_url: str,
    collection_names: list,
    limit: int = 3,
    alpha: float = 0.5
):
    """Search across multiple Weaviate collections"""

    if not collection_names:
        return []

    client = connect_to_weaviate(weaviate_url)
    if not client:
        return []

    try:
        embedding_model = load_embedding_model()
        query_vector = embedding_model.embed_query(query_text)

        all_results = []

        for collection_name in collection_names:
            results = search_single_collection(
                client=client,
                collection_name=collection_name,
                query_text=query_text,
                query_vector=query_vector,
                limit=limit,
                alpha=alpha
            )

            all_results.extend(results)

        # Global sort by distance (smaller = more relevant)
        all_results.sort(key=lambda doc: doc.metadata["distance"])


        return all_results

    except Exception as e:
        st.error(f"Weaviate query error: {e}")
        return []

    finally:
        client.close()

MAX_CONTEXT_CHARS = 20000

def retrieve_docs(state: RAGState):
    docs = query_weaviate(
        state["question"],
        weaviate_url,
        selected_collections,
        search_limit,
        alpha = state["search_alpha"]
    )
    if not docs:
        state["documents"] = []
        state["context"] = ""
        state["answer"] = "⚠️ В выбранной коллекции нет документов или не найдено совпадений."
        state["sources"] = []
        return state


    st.write(f"Найдено чанков до reranking: {len(docs)}")

    unique_docs = {}
    for doc in docs:

        cid = doc.metadata.get("cid")

        if cid not in unique_docs:
            unique_docs[cid] = doc

    docs = list(unique_docs.values())

    docs = rerank_documents(state["question"], docs, top_k=1)

    st.write(f"Найдено чанков после reranking: {len(docs)}")

    # собираем уникальные CID
    doc_sources = list(set([
        (
            doc.metadata.get("cid"),
            doc.metadata.get("collection")
        )
        for doc in docs
        if doc.metadata.get("cid")
    ]))

    # Проверка
    #st.write("CID из retrieval:", doc_sources)
    #st.write("Типы CID:", [type(cid) for cid, _ in doc_sources])

    # загружаем ВСЕ чанки этих документов
    full_docs = []
    seen_cid = set()

    client = None
    try:
        client = connect_to_weaviate(weaviate_url)

        for cid, col in doc_sources:

            if cid in seen_cid:
                continue

            # берем именно ту коллекцию, откуда пришел chunk
            collection = client.collections.get(col)

            st.write(f"Ищем CID {cid} в коллекции {col}")

            response = collection.query.fetch_objects(
                filters=Filter.by_property("cid").equal(cid),
                limit=1000
            )

            st.write(
                "Найдено объектов:",
                len(response.objects) if response else 0
            )

            if response and response.objects:

                seen_cid.add(cid)

                for obj in response.objects:
                    full_docs.append(
                        Document(
                            page_content=obj.properties.get("content", ""),
                            metadata=obj.properties
                        )
                    )

        # st.write("full_docs количество:", len(full_docs))

        if not full_docs:
            state["documents"] = []
            state["context"] = ""
            state["sources"] = []
            state["answer"] = "⚠️ Не удалось загрузить полный документ."
            return state

        #  удаление дубликатов чанков
        seen = set()
        unique_docs = []

        for doc in full_docs:
            key = doc.metadata.get("chunk_id")

            if key not in seen:
                seen.add(key)
                unique_docs.append(doc)

        docs = unique_docs

    finally:
        if client:
            client.close()

    return {
        **state,
        "documents": docs,
        "context": "",
        "sources": [],
        "answer": ""
    }

def rerank_documents(query, docs, top_k=3):
    if not docs:
        return []

    pairs = [(query, doc.page_content) for doc in docs]
    scores = reranker.predict(pairs)

    scored_docs = list(zip(docs, scores))
    scored_docs.sort(key=lambda x: x[1], reverse=True)

    return [doc for doc, _ in scored_docs[:top_k]]


def build_context(state: RAGState):
    context_parts = []
    sources = []

    for doc in state.get("documents", []):

        content = str(doc.page_content)
        distance = float(doc.metadata.get("distance", 1.0))

        context_parts.append(content)

        sources.append({
            "title": str(doc.metadata.get("title", "Unknown")),
            "content": content,
            "distance": distance
        })

    context = "\n\n".join(context_parts)
    st.write("----- DEBUG CONTEXT -----")
    with st.expander("🔍 Debug Context"):
        st.write(context)
    st.write("-------------------------")
    context = context[:MAX_CONTEXT_CHARS]
    #проверка
    st.write("Размер context:", len(context))

    return {
        **state,
        "context": context,
        "sources": sources
    }


def generate_answer(state: RAGState):

    prompt = ChatPromptTemplate.from_template("""
    You are a senior software documentation assistant.

    Answer ONLY using the provided documentation context.

    If the answer exists in the context:
    - give a precise technical answer
    - summarize duplicate information
    - if multiple chunks describe the same thing, combine them
    
    If the user asks for the full specification, then give him the entire document found!
    


    Context:
    {context}

    Question:
    {question}

    Answer:
    """)


    # If the answer does not exist, say exactly:
    # I don't have enough information to answer this question.
    # prompt = ChatPromptTemplate.from_template(
    #     "You are a helpful AI assistant. Answer the question based on the provided context."
    #     "If the question asks to list ALL items, aggregate all relevant pieces from the context and provide a complete list."
    #     "If context does not contain the requested information, just say 'I don't have enough information to answer this question.'\n\n"
    #     "Information:"
    #     "{context}"
    #
    #     "Question:"
    #     "{question}"
    #
    #      "Answer:"
    # )
    # prompt = ChatPromptTemplate.from_template("""
    #     You are a senior software documentation specialist.
    #
    #     Use ONLY the provided information to answer the question.
    #     If the answer is not explicitly present, respond exactly with:
    #     "Insufficient information available."
    #
    #     Do not speculate.
    #     Do not generalize beyond the given information.
    #     Do not mention the source of information.
    #
    #     Format the answer professionally.
    #     Use bullet points where appropriate.
    #     Keep the answer concise and technical.
    #
    #     Information:
    #     {context}
    #
    #     Question:
    #     {question}
    #
    #     Answer:
    # """)

    chain = prompt | state["llm"]
    response = chain.invoke({
        "context": state["context"],
        "question": state["question"]
    })

    # Универсальная обработка ответа
    if hasattr(response, "content"):
        answer_text = response.content
    else:
        answer_text = str(response)

    return {
        **state,
        "answer": answer_text
    }


def build_rag_graph():
    graph = StateGraph(RAGState)

    graph.add_node("retrieve", retrieve_docs)
    graph.add_node("context", build_context)
    graph.add_node("generate", generate_answer)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "context")
    graph.add_edge("context", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")

    llm_provider = st.selectbox(
        "LLM Provider",
        ["Yandex Cloud", "OpenRouter"],
        index=0
    )

    if llm_provider == "Yandex Cloud":
        yandex_api_key = st.text_input(
            "Yandex Cloud API Key",
            type="password",
            value=os.getenv("YANDEX_API_KEY", "")
        )

        yandex_folder_id = st.text_input(
            "Yandex Cloud Folder ID",
            value=os.getenv("YANDEX_FOLDER_ID", "")
        )

        model_name = st.selectbox(
            "Yandex Model",
            ["yandexgpt", "yandexgpt-lite", "summarize"]
        )

    elif llm_provider == "OpenRouter":
        openrouter_api_key = st.text_input(
            "OpenRouter API Key",
            type="password",
            value=os.getenv("OPENROUTER_API_KEY", "")
        )

        model_name = st.text_input(
            "OpenRouter Model",
            value=os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
        )

    search_mode = st.selectbox(
        "Search mode",
        ["Hybrid", "Vector", "BM25"],
        index=0
    )

    if search_mode == "Vector":
        alpha = 0.0
    elif search_mode == "BM25":
        alpha = 1.0
    else:
        alpha = 0.5

    # Weaviate configuration
    weaviate_url = st.text_input(
        "Weaviate URL",
        value=os.getenv("WEAVIATE_URL", "http://localhost:8080"),
        help="Weaviate instance URL"
    )

    available_collections = get_collections_list(weaviate_url)

    if available_collections:

        # --- Группировка по типу ---
        grouped = {}

        for name in available_collections:
            doc_type = name.split("_")[0]  # Component, Guide, Specification
            grouped.setdefault(doc_type, []).append(name)

        # Сортируем типы и коллекции
        for key in grouped:
            grouped[key] = sorted(grouped[key])

        # --- Формируем список опций ---
        options = ["All Documents"]

        for doc_type in sorted(grouped.keys()):
            options.append(f"--- {doc_type} ---")
            options.extend(grouped[doc_type])

        selected_option = st.radio(
            "📚 Select Collection",
            options,
            index=0
        )

        # --- Обработка выбора ---
        if selected_option == "All Documents":
            selected_collections = available_collections

        elif selected_option.startswith("---"):
            # Если пользователь нажал на заголовок типа — выбираем все внутри
            doc_type = selected_option.replace("--- ", "").replace(" ---", "")
            selected_collections = grouped.get(doc_type, [])

        else:
            selected_collections = [selected_option]

    else:
        st.warning("No collections found in Weaviate")
        selected_collections = []

    # Search parameters
    search_limit = st.slider("Search Results Limit", 1, 100, 10)
    chunk_size = st.slider("Text Chunk Size", 500, 2000, 1000)

    # --- View documents inside selected collections ---
    if selected_collections:
        st.markdown("---")
        st.subheader("📂 View Documents")

        if st.button("Show Documents in Selected Collection(s)"):

            client = None
            try:
                client = connect_to_weaviate(weaviate_url)

                for col in selected_collections:
                    st.markdown(f"### 📚 {col}")

                    collection = client.collections.get(col)

                    response_debug = collection.query.fetch_objects(limit=3)

                    for obj in response_debug.objects:
                        st.write("CID в базе:", obj.properties.get("cid"), type(obj.properties.get("cid")))

                    all_objects = []

                    response = collection.query.fetch_objects(limit=100)

                    all_objects.extend(response.objects)

                    while response.objects:
                        response = collection.query.fetch_objects(
                            limit=100,
                            after=response.objects[-1].uuid
                        )
                        all_objects.extend(response.objects)

                    if not all_objects:
                        st.write("— No documents found —")
                    else:
                        from collections import Counter

                        title_counter = Counter()

                        for obj in all_objects:
                            title = obj.properties.get("title", "No title")
                            title_counter[title] += 1

                        st.write(f"Всего чанков: {len(all_objects)}")

                        for title, count in sorted(title_counter.items(), key=lambda x: -x[1]):
                            st.write(f"- {title} ({count} chunks)")

            except Exception as e:
                st.error(f"Error fetching documents: {e}")

            finally:
                if client:
                    client.close()




# Main chat interface
def main():
    # Load models
    embedding_model = load_embedding_model()
    if llm_provider == "Yandex Cloud":
        llm = load_llm(
            provider="Yandex Cloud",
            model=model_name,
            api_key=yandex_api_key,
            folder_id=yandex_folder_id
        )
    else:
        llm = load_llm(
            provider="OpenRouter",
            model=model_name,
            api_key=openrouter_api_key
        )

    if not llm:
        st.warning(f"⚠️ Please configure valid {llm_provider} credentials to start chatting")
        st.info("📝 Steps to get started:")
        st.markdown("""
           1. Go to [Yandex Cloud](https://cloud.yandex.com/) and create an account
           2. Create a folder in Yandex Cloud
           3. Enable the YandexGPT API service
           4. Generate an API key and get Folder ID
           5. Enter the credentials in the sidebar
           """)
        return

    rag_app = build_rag_graph()

    # Display chat history
    for message_index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sources" in message:
                with st.expander("📚 Sources"):
                    for i, source in enumerate(message["sources"], 1):
                        st.markdown(f"**Source {i}:** {source['title']}")
                        st.markdown(f"*Distance: {source.get('distance', 'N/A'):.4f}*")

                        # Используем чекбокс для показа полного контента
                        show_full = st.checkbox(f"Show full content of Source {i}",
                                                key=f"hist_check_{message_index}_{i}")

                        if show_full:
                            st.text_area("",
                                         value=source['content'],
                                         height=200,
                                         key=f"hist_content_{message_index}_{i}")
                        else:
                            content_preview = source['content'][:200] + ("..." if len(source['content']) > 200 else "")
                            st.markdown(f"```\n{content_preview}\n```")

    # Chat input
    if prompt := st.chat_input("Ask me anything about your documents..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching documents and generating response..."):
                try:
                    result = rag_app.invoke({
                        "question": prompt,
                        "llm": llm,
                        "search_alpha": alpha
                    })

                    response = result["answer"]
                    sources = result.get("sources", [])

                    st.markdown(response)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "sources": sources
                    })

                except Exception as e:
                    st.error(f"An error occurred: {e}")


# Sidebar status
with st.sidebar:
    st.markdown("---")
    st.subheader("Status")

    # Check Weaviate connection
    client = None
    try:
        client = connect_to_weaviate(weaviate_url)
        if client:
            if selected_collections:
                st.success("✅ Connected to Weaviate")
                st.info(f"📚 Selected collections: {', '.join(selected_collections)}")
            else:
                st.warning("⚠️ No collections selected")
        else:
            st.error("❌ Cannot connect to Weaviate")
    except:
        st.error("❌ Weaviate connection failed")
    finally:
        if client:
            client.close()

    # Check LLM API
    if llm_provider == "Yandex Cloud":
        if yandex_api_key and yandex_folder_id:
            st.success("✅ Yandex Cloud API key configured")
            st.success("✅ Yandex Cloud Folder ID configured")
            st.info(f"📋 Selected Model: {model_name}")
        else:
            if not yandex_api_key:
                st.error("❌ Yandex Cloud API key missing")
            if not yandex_folder_id:
                st.error("❌ Yandex Cloud Folder ID missing")

    elif llm_provider == "OpenRouter":
        if openrouter_api_key:
            st.success("✅ OpenRouter API key configured")
            st.info(f"📋 Selected Model: {model_name}")
        else:
            st.error("❌ OpenRouter API key missing")

    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.processed = {}

        for key in list(st.session_state.keys()):
            if key.startswith(('hist_check_', 'curr_check_')):
                del st.session_state[key]
        st.rerun()

if __name__ == "__main__":
    main()