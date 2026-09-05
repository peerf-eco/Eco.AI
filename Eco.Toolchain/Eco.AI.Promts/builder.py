import os
import sys
import subprocess
import argparse
from datetime import datetime

# --- БЛОК АВТОМАТИЧЕСКОЙ УСТАНОВКИ ЗАВИСИМОСТЕЙ ---
def install_dependencies():
    try:
        import frontmatter
    except ImportError:
        print("Библиотека 'python-frontmatter' не найдена. Установка...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-frontmatter"])
        print("Установка завершена. Перезапуск скрипта...")
        os.execv(sys.executable, ['python'] + sys.argv)

install_dependencies()
import frontmatter

class EcoPromptBuilder:
    def __init__(self, base_path=".", output_dir="Builds", lang="ru"):
        self.base_path = base_path
        self.output_path = os.path.join(base_path, output_dir)
        self.lang = lang.lower()
        
        # Карта маппинга расширений файлов в языки для Markdown блоков кода
        self.lang_map = {
            '.py': 'python',
            '.c': 'cpp',      # По вашему требованию .c файлы оборачиваем в ```cpp
            '.cpp': 'cpp',
            '.h': 'cpp',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.go': 'go',
            '.rs': 'rust'
        }
        
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

    def _resolve_path(self, rel_path):
        """
        Умное разрешение путей с учетом локализации и расширения файла.
        """
        # Разбиваем путь на части: например, 'Common/constraints.md' -> ('Common', 'constraints.md')
        dir_name, file_name = os.path.split(rel_path)
        ext = os.path.splitext(file_name)[1].lower()

        if ext == '.md':
            # Для MD файлов ищем в подпапке языка: Common/ru/constraints.md
            localized_path = os.path.join(self.base_path, dir_name, self.lang, file_name)
            if os.path.exists(localized_path):
                return localized_path
            
            # Если локализованный файл не найден, пробуем исходный путь прямой вставки
            fallback_path = os.path.join(self.base_path, rel_path)
            if os.path.exists(fallback_path):
                return fallback_path
        else:
            # Для файлов исходного кода (и других, кроме .md) ищем напрямую по указанному пути
            code_path = os.path.join(self.base_path, rel_path)
            if os.path.exists(code_path):
                return code_path
                
        return None

    def build(self, agent_file):
        """
        Собирает агентский промпт на основе метаданных
        """
        agent_full_path = os.path.join(self.base_path, "Agents", agent_file)
        
        if not os.path.exists(agent_full_path):
            raise FileNotFoundError(f"Файл агента не найден: {agent_full_path}")

        agent_recipe = frontmatter.load(agent_full_path)
        
        model = agent_recipe.get("model", "gpt-4")
        temp = agent_recipe.get("temperature", 0.2)
        assembly = agent_recipe.get("assembly", [])

        assembled_content = []
        for rel_path in assembly:
            full_path = self._resolve_path(rel_path)
            
            if not full_path:
                print(f" ⚠️ ПРЕДУПРЕЖДЕНИЕ: Модуль {rel_path} не найден (проверена локаль '{self.lang}').")
                continue

            ext = os.path.splitext(full_path)[1].lower()

            if ext == '.md':
                # Обработка Markdown файлов
                module = frontmatter.load(full_path)
                header = f"<!-- --- MODULE: {rel_path} ({self.lang.upper()}) --- -->"
                assembled_content.append(f"{header}\n{module.content.strip()}")
            
            elif ext in self.lang_map:
                # Обработка файлов с кодом
                lang_marker = self.lang_map[ext]
                with open(full_path, "r", encoding="utf-8") as code_file:
                    code_content = code_file.read().strip()
                
                header = f"<!-- --- CODE MODULE: {rel_path} --- -->"
                formatted_code = f"```{lang_marker}\n{code_content}\n```"
                assembled_content.append(f"{header}\n{formatted_code}")
                
            else:
                # На случай других расширений файлов (например, текстовых или SVG)
                with open(full_path, "r", encoding="utf-8") as raw_file:
                    raw_content = raw_file.read().strip()
                assembled_content.append(raw_content)

        final_prompt_text = "\n\n".join(assembled_content)

        # Формируем имя файла (теперь .md на выходе)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        agent_name = os.path.splitext(agent_file)[0]
        file_name = f"build_{agent_name}_{self.lang}_{timestamp}.md"
        save_path = os.path.join(self.output_path, file_name)

        # Запись итогового файла
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(f"<!--\nAGENT: {agent_name}\nLANG: {self.lang.upper()}\nMODEL: {model}\nTEMPERATURE: {temp}\n-->\n\n")
            f.write(final_prompt_text)

        return {
            "text": final_prompt_text,
            "model": model,
            "temp": temp,
            "save_path": save_path
        }

if __name__ == "__main__":
    # Настраиваем разбор аргументов командной строки
    parser = argparse.ArgumentParser(description="Eco AI Prompt Builder")
    parser.add_argument("agents", nargs="*", help="Список файлов агентов (.md)")
    parser.add_argument("--lang", default="ru", choices=["ru", "en"], help="Язык сборки (по умолчанию: ru)")
    
    args = parser.parse_args()

    builder = EcoPromptBuilder(base_path=".", lang=args.lang)
    agent_files = args.agents

    # Если файлы не переданы, ищем все в папке Agents/
    if not agent_files:
        print(f"Попытка сборки всех агентов по умолчанию из папки Agents/ (Язык: {args.lang.upper()})...")
        agents_dir = os.path.join(".", "Agents")
        if os.path.exists(agents_dir):
            agent_files = [f for f in os.listdir(agents_dir) if f.endswith(".md")]
        else:
            print(f"[Ошибка] Папка {agents_dir} не найдена.")
            sys.exit(1)

    print(f"--- Запуск сборки Eco AI Агентов (Язык: {args.lang.upper()} | Всего: {len(agent_files)}) ---")
    print("-" * 50)

    for agent_file in agent_files:
        try:
            result = builder.build(agent_file)
            print(f"[Успех] Агент: {agent_file}")
            print(f"  └─ Файл: {result['save_path']}")
            print(f"  └─ Модель: {result['model']} | Temp: {result['temp']}")
            print("-" * 50)
        except FileNotFoundError:
            print(f"[Пропуск] Файл Agents/{agent_file} не найден.")
        except Exception as e:
            print(f"[Ошибка] Не удалось собрать {agent_file}: {e}")

    print(f"\nГотово. Результаты сохранены в папку ./Builds/")
