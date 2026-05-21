from transformers import AutoTokenizer, AutoModel
from dotenv import load_dotenv
import torch
import weaviate
from weaviate.classes.config import Property, DataType
import json
import os


# =========================
# SETTINGS
# =========================

json_folder = os.path.normpath("../Files/json")
json_path = os.path.join(json_folder, "documentation_mapping.json")

load_dotenv()

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL"
)

COLLECTIONS = {
    ("component", "RU"): "Component_RU",
    ("component", "EN"): "Component_EN",
    ("specification", "RU"): "Specification_RU",
    ("specification", "EN"): "Specification_EN",
    ("guide", "RU"): "Guide_RU",
    ("guide", "EN"): "Guide_EN",
}

DEFAULT_COLLECTION = "Document"

# =========================
# MODEL
# =========================

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)


# Replace with a model better suited for Russian
# tokenizer = AutoTokenizer.from_pretrained("DeepPavlov/rubert-base-cased")
# model = AutoModel.from_pretrained("DeepPavlov/rubert-base-cased")

# =========================
# WEAVIATE
# =========================

# Connect to Weaviate
client = weaviate.connect_to_local()
print(client.is_ready())  # Should print: `True`

# =========================
# CREATING COLLECTIONS
# =========================

def create_collections():
    for name in set(COLLECTIONS.values()):
        if not client.collections.exists(name):
            client.collections.create(
                name,
                properties=[
                    Property(name="chunk_id", data_type=DataType.TEXT, description="ID чанка документа"),
                    Property(name="documentType", data_type=DataType.TEXT, description="Тип документа"),
                    Property(name="content", data_type=DataType.TEXT, description="Текст документа"),

                    Property(name="fileName", data_type=DataType.TEXT, description="Название файла документа"),
                    Property(name="title", data_type=DataType.TEXT, description="Название документа"),
                    Property(name="component", data_type=DataType.TEXT, description="Название компонента"),
                    Property(name="description", data_type=DataType.TEXT, description="Краткое описание компонента"),
                    Property(name="interface", data_type=DataType.TEXT, description="Название интерфейса"),

                    Property(name="cid", data_type=DataType.TEXT, description="ID документа"),
                    Property(name="tags", data_type=DataType.TEXT, description="теги компонента"),

                    Property(name="registryUrl", data_type=DataType.TEXT, description="Ссылка на офф сайт компонента"),
                    Property(name="source", data_type=DataType.TEXT, description="Источник компонента на GitHub"),

                    Property(name="version", data_type=DataType.TEXT, description="Версия документа"),
                    Property(name="lastModified", data_type=DataType.TEXT, description="Последнее время обновления"),
                    Property(name="language", data_type=DataType.TEXT, description="Язык документа"),
                ]
            )
            print(f"✅ Коллекция {name} создана")
        else:
            print(f"ℹ️ Коллекция {name} уже существует")

create_collections()

# =========================
# EMBEDDING
# =========================

# Define the function before it's called
def embed_and_store(text):
    # Tokenize with a higher max length for Russian text
    inputs = tokenizer(
        text,
        return_tensors='pt',
        truncation=True,
        padding=True,
        max_length=512)  # Increased max_length

    with torch.no_grad():
        # Get embeddings from the last hidden state
        outputs = model(**inputs)
        # Use mean pooling for sentence embeddings
        embeddings = outputs.last_hidden_state.mean(dim=1).numpy()[0]

    return embeddings.tolist()

# =========================
#  COLLECTION SELECTION
# =========================

def get_collection(doc):
    doc_type = doc.get("type", "").strip().lower()
    lang = doc.get("metadata", {}).get("language", "EN").strip().upper()

    key = (doc_type, lang)

    if key not in COLLECTIONS:
        print(f"⚠️ Unknown key: {key}")
        return DEFAULT_COLLECTION

    return COLLECTIONS[key]

# =========================
# LOAD JSON FILES
# =========================



json_files = [f for f in os.listdir(json_folder) if f.endswith(".json")]

for json_file_name in json_files:
    json_path = os.path.join(json_folder, json_file_name)
    print(f"\n📄 Загружаем файл: {json_file_name}")

    with open(json_path, encoding="utf-8") as f:
        documents = json.load(f)

    total = len(documents)

    for i, doc in enumerate(documents):
        try:
            text = doc["content"]

            metadata = doc["metadata"]

            collection_name = get_collection(doc)
            docs = client.collections.get(collection_name)

            vector = embed_and_store(text)

            docs.data.insert(
                properties={
                    # основной контент
                    "chunk_id": doc.get("chunk_id"),
                    "documentType": doc.get("type"),
                    "content": text,

                    # базовая информация
                    "fileName": metadata.get("fileName"),
                    "title": metadata.get("title"),
                    "component": metadata.get("component"),
                    "description": metadata.get("description"),
                    "interface": metadata.get("interface"),

                    # идентификация
                    "cid": metadata.get("cid"),
                    "tags": metadata.get("tags"),

                    # ссылки / источники
                    "registryUrl": metadata.get("registryUrl"),
                    "source": metadata.get("source"),

                    # версия и язык
                    "version": metadata.get("version"),
                    "lastModified": metadata.get("lastModified"),
                    "language": metadata.get("language"),
                },
                vector=vector
            )

            print(f"   {i+1}/{total} → {collection_name}")

        except Exception as e:
            print(f"❌ Ошибка в документе {i}: {e}")

client.close()

print("\n🚀 Все документы загружены в нужные коллекции!")

def print_all_schemas():
    client = weaviate.connect_to_local()

    try:
        print("=== WEAVIATE SCHEMA ===")

        for name in [
            "Component_RU", "Component_EN",
            "Specification_RU", "Specification_EN",
            "Guide_RU", "Guide_EN"
        ]:
            if client.collections.exists(name):
                col = client.collections.get(name)
                config = col.config.get()

                print(f"\n📚 {name}")
                for prop in config.properties:
                    print(f"   - {prop.name}: {prop.data_type}")

    finally:
        client.close()

# Uncomment the line below to print the schema after loading documents
print_all_schemas()