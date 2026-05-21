# Search App 🤖

**Search App** is an AI-powered application for semantic search across documents using a vector database (Weaviate) and Large Language Models (LLM) such as OpenAI, OpenRouter, or YandexGPT.

The application allows you to:

* convert text documents into structured JSON format
* upload documents into Weaviate Vector Database via Docker
* perform semantic search across documents
* interact with an AI assistant through a web interface

---

# 🚀 Features

* 📄 Convert Markdown / TXT → JSON
* 🧠 Generate embeddings using HuggingFace Transformers
* 🗄️ Store document vectors in Weaviate Vector Database
* 🔎 Perform semantic search using vector similarity
* 🤖 AI assistant powered by:

  * OpenRouter (OpenAI models)
  * YandexGPT
* 🌐 Web interface built with Streamlit
* 🐳 Docker support for database deployment

---

# 🏗️ Architecture

Processing pipeline:

```
Text / Markdown Files
        ↓
text_to_json.py
        ↓
JSON files
        ↓
Docker (Weaviate)
        ↓
json_to_docker.py
        ↓
Weaviate Vector Database
        ↓
run_app.py
        ↓
Web Application (Streamlit)
```

---

# 📂 Project Structure

```
Search-App/
│
├── text_to_json.py       # Converts documents to JSON
├── json_to_docker.py     # Uploads JSON to Weaviate
├── run_app.py            # Starts the web application
├── app_weaviate.py       # Core AI application logic
├── requirements.txt      # Python dependencies
├── .env                  # API keys and configuration
│
├── Files/
│   ├── text_files/      # Source documents
│   └── json/            # Generated JSON files
```

---

# ⚙️ Requirements

* Python 3.10+
* Docker
* Docker Compose
* API key from one of the providers:

  * OpenRouter API Key
    OR
  * Yandex Cloud API Key + Folder ID

---

# 📦 Installation

## 1. Clone the repository

```
git clone https://github.com/MmOKe666/Search-Documet.git
cd Search-Documet
```

---

## 2. Install dependencies

```
pip install -r requirements.txt
```

Main libraries used:

* streamlit
* weaviate-client
* langchain
* transformers
* torch
* sentence-transformers
* python-dotenv

---

## 3. Configure environment variables

Create a `.env` file:

```
WEAVIATE_URL=http://localhost:8080

OPENROUTER_API_KEY=your_api_key
OPENROUTER_MODEL=openai/gpt-3.5-turbo

YANDEX_API_KEY=your_key
YANDEX_FOLDER_ID=your_folder_id

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

---

# 🐳 Run Weaviate using Docker

In the project folder, run:

```
docker-compose up -d
```

Verify that containers are running:

```
docker ps
```

---

# 📄 Step 1 — Convert documents

Place your documents in:

```
Files/text_files/
```

Run:

```
python text_to_json.py
```

Output:

```
Files/json/*.json
```

---

# 🗄️ Step 2 — Upload documents to Weaviate

```
python json_to_docker.py
```

Documents will be:

* converted into embeddings
* uploaded into vector database collections

---

# 🤖 Step 3 — Start the AI application

```
python run_app.py
```

The application will open in your browser:

```
http://localhost:8501
```

---

# 💬 Usage

In the web interface, you can:

* select an AI provider
* select document collections
* ask questions in natural language
* receive AI-generated answers based on document content

---

# 🖥️ User Interface

The application provides a web interface with a sidebar for configuring the AI assistant and search settings.

## Sidebar Options

**AI Provider**
Select the language model provider (OpenRouter or YandexGPT) used to generate responses.

**Model Selection**
Choose the specific LLM model. Different models provide different response quality, speed, and cost.

**Document Collections**
Select one or more document collections stored in the vector database. The AI assistant will search only within the selected collections.

**Search Method (Hybrid Search)**
The system uses **hybrid search**, which combines:

* **Vector search** — finds semantically similar content using embeddings
* **Keyword search** — finds exact matches based on keywords

A parameter called **alpha** controls the balance:

* **alpha = 0** → keyword search only (exact matching)
* **alpha = 1** → vector search only (semantic similarity)
* **0 < alpha < 1** → hybrid search (recommended)

Hybrid search improves accuracy by combining semantic understanding with exact keyword matching.

---

## Main Interface

The main area allows the user to enter questions and receive AI-generated answers based on the selected document collections.

---

# 🧠 Technologies Used

* Python
* Streamlit
* Weaviate
* LangChain
* Transformers
* HuggingFace
* Docker
* OpenRouter API
* YandexGPT

---

# 🔎 Example

Question:

```
How does the component initialization work?
```

Response:

```
• Component initialization starts with configuration loading  
• Required dependencies are injected  
• System registers component in registry  
```

---

# 🛠️ Troubleshooting

If Weaviate connection fails:

```
docker-compose up -d
```

If dependency errors occur:

```
pip install -r requirements.txt
```

---

# 👤 Author

GitHub: https://github.com/MmOKe666
