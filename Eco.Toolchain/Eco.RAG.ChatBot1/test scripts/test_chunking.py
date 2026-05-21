from sentence_transformers import SentenceTransformer, util
import numpy as np
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS_PATH = os.path.join(BASE_DIR, "Files", "json", "documentation_mapping_md.json")

# === модель ===
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

# === данные ===
with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

documents = [doc["content"] for doc in data]

# === queries ===
queries = [
    {
        "query": "Что делает функция connect?",
        "relevant": "Функция устанавливает соединение с указанным сокетом."
    },
    {
        "query": "Что делает функция ntohs?",
        "relevant": "Функция преобразует u_short из сетевого порядка байтов TCP/IP в порядок байтов хоста."
    }
]

# === embeddings ===
doc_embeddings = model.encode(documents, convert_to_tensor=True)

# === поиск ===
def search(query, top_k=5):
    query_embedding = model.encode(query, convert_to_tensor=True)
    scores = util.cos_sim(query_embedding, doc_embeddings)[0]

    scores_np = scores.cpu().numpy()
    top_results = np.argsort(-scores_np)[:top_k]

    return [(documents[i], scores_np[i]) for i in top_results]

# === evaluation ===
def evaluate(queries, k=5):
    recall_scores = []
    mrr_scores = []

    print("\n" + "="*60)
    print("EVALUATION START")
    print("="*60)

    for q in queries:
        print(f"\n🔎 QUERY: {q['query']}")

        retrieved = search(q["query"], top_k=k)

        rank = None

        for i, (chunk, score) in enumerate(retrieved):
            is_correct = q["relevant"].lower() in chunk.lower()

            if is_correct and rank is None:
                rank = i + 1

            print(f"\n{i+1}. Score: {score:.4f}")
            print("   ", chunk[:150].replace("\n", " "))

            if is_correct:
                print("   ✅ MATCH")

        if rank:
            recall_scores.append(1)
            mrr_scores.append(1 / rank)
            print(f"\n🎯 Found at position: {rank}")
        else:
            recall_scores.append(0)
            mrr_scores.append(0)
            print("\n❌ NOT FOUND")

        print("-"*60)

    recall = sum(recall_scores) / len(recall_scores)
    mrr = sum(mrr_scores) / len(mrr_scores)

    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    print(f"Recall@{k}: {recall:.3f}")
    print(f"MRR: {mrr:.3f}")

    return recall, mrr


# === запуск ===
if __name__ == "__main__":
    evaluate(queries, k=5)