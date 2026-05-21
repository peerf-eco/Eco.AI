import json
import os
import uuid
import re
import yaml
from langchain.text_splitter import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)

text_folder = os.path.normpath("../Files/text_files")
json_folder = os.path.normpath("../Files/json")
base_filename = "documentation_mapping_md"
extension = ".json"

documents = []

CHUNK_SIZE = 800
CHUNK_OVERLAP = 50


# def chunk_text(text):
#     splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
#         tokenizer,
#         chunk_size=400,        # tokens 512 - max
#         chunk_overlap=0,      # перекрытие
#         separators=[
#             "\n\n\n",
#             "\n\n",
#             "\n",
#             " "
#         ]
#     )
#     return splitter.split_text(text)


import re

def split_into_chunks(text):
    chunks = []

    # === 1. OVERVIEW (раздел 1) ===
    overview_match = re.search(r"(^|\n)1\..*?(?=\n2\.|\Z)", text, re.DOTALL)

    if overview_match:
        overview_chunk = overview_match.group(0).strip()
        chunks.append({
            "text": overview_chunk,
            "interface": None
        })

        # удаляем его из текста, чтобы он больше не попался
        text = text.replace(overview_chunk, "", 1)

    # === 2. COMPONENT (раздел 2) ===
    component_match = re.search(r"(^|\n)2\..*?(?=\n3\.|\Z)", text, re.DOTALL)

    if component_match:
        component_chunk = component_match.group(0).strip()
        chunks.append({
            "text": component_chunk,
            "interface": None
        })

        # удаляем из текста
        text = text.replace(component_chunk, "", 1)

    # === 3. ИНТЕРФЕЙСЫ ===
    interface_blocks = re.finditer(r"\n\d+\.\s+.*?(Интерфейс|Interface).*?(?=\n\d+\.\s+.*?(Интерфейс|Interface)|\Z)",text,re.DOTALL)

    for interface in interface_blocks:
        interface_text = interface.group(0)

        interface_name_match = re.search(
            r"([A-Za-z0-9_]+)\s+(Interface|Интерфейс)|"
            r"(Интерфейс|Interface)\s+([^\n]+)",
            interface_text
        )

        interface_name = "Unknown"

        if interface_name_match:
            if interface_name_match.group(1):
                interface_name = interface_name_match.group(1)
            else:
                interface_name = interface_name_match.group(4)

        # добавляем описание интерфейса как отдельный чанк
        header_match = re.match(
            r".*?(?=\n\d+\.\d+\.\d+\.)",
            interface_text,
            re.DOTALL
        )
        if header_match:
            chunks.append({
                "text": header_match.group(0).strip(),
                "interface": interface_name
            })

        # === 4. ФУНКЦИИ внутри интерфейса ===
        function_matches = list(re.finditer(
            r"\d+\.\d+\.\d+\.\s+[^\n]*(Функция|function)",
            interface_text
        ))

        for i in range(len(function_matches)):
            start = function_matches[i].start()
            end = function_matches[i + 1].start() if i + 1 < len(function_matches) else len(interface_text)

            func_chunk = interface_text[start:end].strip()

            # Удаление лишних Error codes
            func_chunk = re.split(r"\n\d+\.\s+(Коды ошибок|Error codes)", func_chunk)[0]

            # 🔥 добавляем имя интерфейса в начало чанка
            prefix = "Interface" if "Interface" in interface_text else "Интерфейс"

            func_chunk = f"{prefix} {interface_name}\n{func_chunk}"

            chunks.append({
                "text": func_chunk,
                "interface": interface_name
            })

    # === 5. ERROR CODES ===
    errors_match = re.search(
        r"\n(?:\d+\.\s+)?(?:Коды ошибок|Error codes)\s*.*?(?=\n(?:Appendix|Приложение)|\Z)",
        text,
        re.DOTALL | re.IGNORECASE
    )

    if errors_match:
        error_chunk = errors_match.group(0).strip()

        chunks.append({
            "text": error_chunk,
            "interface": None
        })

    # Удаление дубликатов
    seen = set()
    unique_chunks = []

    for chunk in chunks:
        key = (chunk["text"], chunk.get("interface"))

        if key not in seen:
            seen.add(key)
            unique_chunks.append(chunk)

    chunks = unique_chunks

    return chunks

def chunk_text(text):
    return split_into_chunks(text)

def split_front_matter(content):
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) == 3:
            yaml_part = parts[1]
            markdown_part = parts[2]
            return yaml.safe_load(yaml_part), markdown_part.strip()
    return {}, content

def clean_markdown(text: str) -> str:
    # Удаляем блоки кода ```cpp ... ```
    # text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

    # Удаляем inline код `
    #text = re.sub(r"`", "", text)

    # Удаляем изображения
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"!image", "", text)

    # Удаляем spoiler блоки
    text = re.sub(r"<spoiler.*?>", "", text)
    text = re.sub(r"</spoiler>", "", text)

    # Удаляем HTML якоря
    text = re.sub(r"<a id=.*?>", "", text)
    text = re.sub(r"</a>", "", text)

    # Удаляем Markdown заголовки
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

    # Удаляем лишние ****
    text = text.replace("****", "")

    # Удаляем лишние **
    text = text.replace("**", "")

    # Убираем лишние пустые строки
    text = re.sub(r"\n\s*\n", "\n\n", text)

    # Удаляем markdown ссылки, оставляя текст
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Удаляем markdown таблицы
    #text = re.sub(r"\|.*?\|\n", "", text)

    # Удаляем строку Table of Contents
    text = re.sub(r"Table of Contents.*?\n", "", text)

    return text.strip()

def remove_content_block(text):

    new_text = re.sub(
        r"## Table of Contents.*?(?=\n# |\n\d+\.\s|\Z)",
        "",
        text,
        flags=re.DOTALL
    )

    if new_text == text and "Table of Contents" in text:
        parts = text.split("Table of Contents", 1)
        text_after = parts[1]

        match = re.search(r"\n\d+\.\s", text_after)
        if match:
            return text_after[match.start():]

    return new_text

def remove_spoiler_content(text):
    return re.sub(
        r'<spoiler\s+title=["\']content["\'].*?>.*?</spoiler>',
        '',
        text,
        flags=re.DOTALL | re.IGNORECASE
    ).strip()

def detect_language(metadata, text):
    # 1. По source (RU.ECO / EN.ECO)
    source = metadata.get("source", "")
    if "RU.ECO" in source:
        return "RU"
    if "EN.ECO" in source:
        return "EN"

    # 2. По имени файла
    filename = metadata.get("fileName", "")
    if "RU." in filename:
        return "RU"
    if "EN." in filename:
        return "EN"

    # 3. По кириллице в тексте
    if re.search(r"[А-Яа-я]", text):
        return "RU"

    # 4. По умолчанию
    return "EN"


os.makedirs(json_folder, exist_ok=True)

for file_name in os.listdir(text_folder):
    if file_name.endswith(".md"):
        file_path = os.path.join(text_folder, file_name)

        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        text = remove_spoiler_content(raw_content)
        text = remove_content_block(text)

        metadata, markdown_content = split_front_matter(text)

        markdown_content = clean_markdown(markdown_content)

        metadata["language"] = detect_language(metadata, markdown_content)

        print("Detected language:", metadata["language"])

        chunks = chunk_text(markdown_content)

        clean_title = metadata.get("title", "")
        if clean_title:
            clean_title = clean_title.replace("****", "")
            clean_title = clean_title.replace("**", "")
            clean_title = clean_title.strip()

        for i, chunk in enumerate(chunks):
            chunk_document = {
                "chunk_id": f"{file_name}_chunk_{i + 1}",
                "type": metadata.get("documentType", "unknown"),
                "content": chunk["text"],
                "metadata": {
                    "fileName": file_name,
                    "title": clean_title,
                    "component": metadata.get("componentName", ""),
                    "description": metadata.get("description", ""),
                    "interface": chunk.get("interface", None),
                    "cid": metadata.get("CID", ""),
                    "tags": metadata.get("tags", ""),
                    "registryUrl": metadata.get("registryUrl", ""),
                    "source": metadata.get("source", ""),
                    "version": metadata.get("version", ""),
                    "lastModified": metadata.get("lastModified", ""),
                    "language": metadata.get("language", "EN")
                }
            }

            documents.append(chunk_document)


json_path = os.path.join(json_folder, base_filename + extension)
suffix = 1

while os.path.exists(json_path):
    json_path = os.path.join(json_folder, f"{base_filename}_{suffix}{extension}")
    suffix += 1

with open(json_path, "w", encoding="utf-8") as json_file:
    json.dump(documents, json_file, indent=4, ensure_ascii=False)

print(f"JSON-файл создан: {json_path}")