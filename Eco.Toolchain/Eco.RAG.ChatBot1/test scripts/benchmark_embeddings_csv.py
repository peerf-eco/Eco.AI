import os
import csv
import datetime
import time
import torch
from dotenv import load_dotenv
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor

import weaviate
from weaviate.connect import ConnectionParams

from sentence_transformers import SentenceTransformer

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {DEVICE}")

# =========================
# Load environment variables
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / "main_scripts" / ".env"

load_dotenv(env_path)

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
)

# if not MODEL_NAME:
#     raise ValueError("EMBEDDING_MODEL not set in .env")

RESULTS_SUMMARY = []

MODELS_TO_TEST = [
     "sentence-transformers/all-MiniLM-L6-v2",
     "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
     "BAAI/bge-m3",
     "Qwen/Qwen3-Embedding-0.6B",
     "nomic-ai/nomic-embed-text-v2-moe",
     "ai-forever/FRIDA",
]
MODEL_SUFFIX = {
     "sentence-transformers/all-MiniLM-L6-v2": "minilm",
     "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": "mpnet",
     "BAAI/bge-m3": "bge",
     "Qwen/Qwen3-Embedding-0.6B": "Qwen3",
     "nomic-ai/nomic-embed-text-v2-moe": "nomic",
     "ai-forever/FRIDA": "frida"
}

if MODEL_NAME:
    print(f"Using single model from .env: {MODEL_NAME}")
    MODELS_TO_RUN = [MODEL_NAME]
else:
    print("No EMBEDDING_MODEL set, testing all models")
    MODELS_TO_RUN = MODELS_TO_TEST

# =========================
# Loading Models
# =========================

def load_model(model_name):

    print("\n========================")
    print(f"Loading model: {model_name}")
    print("========================")

    load_start = time.time()

    CPU_ONLY_MODELS = [
        "nomic-ai/nomic-embed-text-v2-moe",
        "ai-forever/FRIDA"
    ]

    if model_name in CPU_ONLY_MODELS:
        device = "cpu"
    else:
        device = DEVICE

    model = SentenceTransformer(
        model_name,
        device=device,
        trust_remote_code=True
    )

    load_time = time.time() - load_start

    print(f"Load time: {load_time:.2f} sec")

    if DEVICE == "cuda":
        vram = torch.cuda.memory_allocated() / 1024**2
        print(f"VRAM used: {vram:.2f} MB")

    print(f"Embedding size: {model.get_sentence_embedding_dimension()}")

    # throughput test
    test_texts = TEST_QUESTIONS * 20

    if DEVICE == "cuda":
        torch.cuda.synchronize()

    start = time.time()

    model.encode(test_texts, batch_size=32)

    if DEVICE == "cuda":
        torch.cuda.synchronize()

    batch_throughput = len(test_texts) / (time.time() - start)

    print(f"Batch throughput: {batch_throughput:.2f} texts/sec")

    # Real throughput (single queries)
    if DEVICE == "cuda":
        torch.cuda.synchronize()

    start = time.time()

    for q in TEST_QUESTIONS * 5:
        model.encode([q])

    if DEVICE == "cuda":
        torch.cuda.synchronize()

    real_throughput = (len(TEST_QUESTIONS) * 5) / (time.time() - start)

    print(f"Real throughput: {real_throughput:.2f} texts/sec")

    return model, load_time, batch_throughput, real_throughput

# =========================
# Test questions
# =========================

TEST_QUESTIONS = [

    # Основные вопросы
    "What is Eco.List1 component?",
    "What does Add function do in Eco.List1?",
    "What is tree data structure?",
    "What does get_LeastCommonAncestor function do?",
    "Что такое структура данных дерево?",

    # Общие вопросы о компонентах
    "What is Eco.Tree1 component?",
    "What is Eco.List1 component?",
    "What does Eco.Tree1 implement?",
    "What does Eco.List1 implement?",

    # Tree structure questions
    "What is a tree data structure?",
    "What is a tree node?",
    "What is a root node in a tree?",
    "What is a leaf node?",
    "What is the difference between root and leaf node?",
    "What is depth in a tree?",
    "What is height in a tree?",

    # Tree API questions
    "What does CreateNode function do?",
    "What does InsertNode function do?",
    "What does DeleteNode function do?",
    "What does Clear function do in Eco.Tree1?",

    # Tree node interface questions
    "What does get_Parent function return?",
    "What does AddChild function do?",
    "How to add child node in Eco.Tree1Node?",

    # List questions
    "What is Eco.List1?",
    "What is list data structure?",
    "What does Count function do in Eco.List1?",
    "What does Remove function do?",
    "What does RemoveAt function do?",
    "What does InsertAt function do?",
    "What does IndexOf function do?",
    "What does Clear function do in Eco.List1?",

    # Practical usage questions
    "How to add element to list?",
    "How to remove element from list?",
    "How to get element by index?",
    "How to clear a list?",

    # Russian questions (important for multilingual testing)
    "Что такое компонент Eco.Tree1?",
    "Что такое компонент Eco.List1?",
    "Что такое узел дерева?",
    "Что делает функция Add?",
    "Что делает функция Remove?",
    "Что делает функция Clear?",
    "Как добавить элемент в список?",
    "Как удалить элемент из списка?",
]

# =========================
# CSV setup
# =========================

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

CSV_FILENAME = f"embedding_benchmark_all_models_{timestamp}.csv"


# =========================
# Connect to Weaviate v4
# =========================

print(f"Connecting to Weaviate: {WEAVIATE_URL}")

client = weaviate.WeaviateClient(
    connection_params=ConnectionParams.from_url(
        url=WEAVIATE_URL,
        grpc_port=50051
    )
)

client.connect()


# =========================
# Get collections from Weaviate
# =========================

def get_available_collections():

    collections = client.collections.list_all()

    return list(collections.keys())


def filter_target_collections(collections):

    prefixes = ["Component", "Specification", "Guide"]

    result = []

    for col in collections:
        if any(col.startswith(prefix) for prefix in prefixes):
            result.append(col)

    return result


def get_collections_for_model(collections, suffix):

    # если одна модель → используем базовые коллекции
    if suffix is None:
        return [c for c in collections if c.count("_") == 1]

    # если несколько моделей → используем suffix
    return [c for c in collections if c.endswith(suffix)]

# =========================
# Search function
# =========================

def search_all_collections(question, model, suffix):

    all_collections = get_available_collections()

    filtered = filter_target_collections(all_collections)

    collection_names = get_collections_for_model(filtered, suffix)
    print("Searching in collections:", collection_names)

    embed_start = time.time()

    query_vector = model.encode(
        question,
        normalize_embeddings=True
    ).tolist()

    embed_time = time.time() - embed_start

    search_start = time.time()

    print(f"Embedding time: {embed_time*1000:.2f} ms")

    all_results = []

    def search_collection(collection_name):

        local_results = []

        if not client.collections.exists(collection_name):
            print(f"⚠️ Collection not found: {collection_name}")
            return []

        collection = client.collections.get(collection_name)

        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=1,
            return_metadata=["distance"]
        )

        for obj in response.objects:

            distance = obj.metadata.distance
            similarity = 1 - distance

            content = obj.properties.get("content", "")

            local_results.append({
                "collection": collection_name,
                "similarity": similarity,
                "content": content
            })

        return local_results

    # параллельный поиск
    with ThreadPoolExecutor(max_workers=6) as executor:

        futures = [executor.submit(search_collection, col) for col in collection_names]

        for future in futures:
            all_results.extend(future.result())

    all_results.sort(key=lambda x: x["similarity"], reverse=True)

    search_time = time.time() - search_start

    print(f"Embedding: {embed_time*1000:.2f} ms | Search: {search_time*1000:.2f} ms")

    return all_results[:3], embed_time, search_time


# =========================
# Benchmark
# =========================

def run_benchmark(model, model_name, batch_throughput, real_throughput, suffix):

    similarities = []
    embed_times = []
    search_times = []

    print("\nStarting benchmark...\n")

    file_exists = os.path.exists(CSV_FILENAME)

    with open(CSV_FILENAME, mode="a", newline="", encoding="utf-8") as file:

        writer = csv.writer(file, delimiter=";")

        if not file_exists:
            writer.writerow([
                "model",
                "batch_throughput",
                "real_throughput",
                "question",
                "rank",
                "collection",
                "similarity",
                "preview"
            ])

        for question in TEST_QUESTIONS:

            print(f"\nQuestion: {question}")

            results, embed_time, search_time = search_all_collections(
                question,
                model,
                suffix
            )
            embed_times.append(embed_time)
            search_times.append(search_time)

            if not results:
                print("No results found")
                continue

            for rank, result in enumerate(results, start=1):
                similarity = result["similarity"]
                content = result["content"]
                collection = result["collection"]

                similarities.append(similarity)

                preview = content[:100].replace("\n", " ")

                print(f"Rank {rank} | Collection: {collection} | Similarity: {similarity:.4f}")

                writer.writerow([
                    model_name,
                    batch_throughput,
                    real_throughput,
                    question,
                    rank,
                    collection,
                    similarity,
                    preview
                ])

    if similarities:
        avg_similarity = sum(similarities) / len(similarities)
    else:
        avg_similarity = 0

    avg_embed_time = sum(embed_times) / len(embed_times)
    avg_search_time = sum(search_times) / len(search_times)


    print("\n========================")
    print("Benchmark complete")
    print(f"Model: {model_name}")
    print(f"Average similarity: {avg_similarity:.4f}")
    print(f"Average embedding time: {avg_embed_time * 1000:.2f} ms")
    print(f"Average search time: {avg_search_time * 1000:.2f} ms")
    print(f"CSV saved to: {CSV_FILENAME}")
    print("========================\n")

    RESULTS_SUMMARY.append({
        "model": model_name,
        "batch_throughput": batch_throughput,
        "real_throughput": real_throughput,
        "avg_similarity": avg_similarity,
        "avg_embed_ms": avg_embed_time * 1000,
        "avg_search_ms": avg_search_time * 1000,
        "vram_mb": torch.cuda.memory_allocated() / 1024 ** 2 if DEVICE == "cuda" else 0
    })

# =========================
# Winner
# =========================

def select_winner():

    print("\n========================")
    print("MODEL RANKING")
    print("========================")

    scored = []

    for r in RESULTS_SUMMARY:

        # normalize scores
        speed_score = r["real_throughput"]
        quality_score = r["avg_similarity"] * 1000
        latency_score = -r["avg_embed_ms"]
        vram_score = -r["vram_mb"] * 0.1

        total_score = (
            speed_score * 0.4 +
            quality_score * 0.4 +
            latency_score * 0.1 +
            vram_score * 0.1
        )

        scored.append((total_score, r))

    scored.sort(reverse=True, key=lambda x: x[0])

    for rank, (score, r) in enumerate(scored, 1):
        print(
            f"{rank}. {r['model']}\n"
            f"   Score: {score:.2f}\n"
            f"   Batch throughput: {r['batch_throughput']:.1f}\n"
            f"   Real throughput: {r['real_throughput']:.1f}\n"
            f"   Similarity: {r['avg_similarity']:.4f}\n"
            f"   Embed: {r['avg_embed_ms']:.1f} ms\n"
            f"   VRAM: {r['vram_mb']:.0f} MB\n"
        )

    winner = scored[0][1]

    print("🏆 WINNER:")
    print(winner["model"])
    print("========================\n")

# =========================
# Run
# =========================

if __name__ == "__main__":

    results_summary = []

    for model_name in MODELS_TO_RUN:
        try:
            model, load_time, batch_throughput, real_throughput = load_model(model_name)

            embedding_dim = model.get_sentence_embedding_dimension()

            model_suffix = MODEL_SUFFIX[model_name]

            full_suffix = f"{model_suffix}_{embedding_dim}"

            # если одна модель — используем стандартные коллекции
            suffix = None if len(MODELS_TO_RUN) == 1 else full_suffix

            run_benchmark(
                model,
                model_name,
                batch_throughput,
                real_throughput,
                suffix
            )

        except Exception as e:
            print(f"\n❌ Model failed: {model_name}")
            print(e)
            continue

        finally:
            if 'model' in locals():
                del model
            if DEVICE == "cuda":
                torch.cuda.empty_cache()

    select_winner()

    client.close()