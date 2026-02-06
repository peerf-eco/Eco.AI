
import os
import sys
import subprocess
from datetime import datetime

# --- БЛОК АВТОМАТИЧЕСКОЙ УСТАНОВКИ ЗАВИСИМОСТЕЙ ---
def install_dependencies():
    try:
        import frontmatter
    except ImportError:
        print("Библиотека 'python-frontmatter' не найдена. Установка...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-frontmatter"])
        print("Установка завершена. Перезапуск скрипта...")
        # Перезапускаем текущий скрипт, чтобы подхватить новую библиотеку
        os.execv(sys.executable, ['python'] + sys.argv)

install_dependencies()
import frontmatter

class EcoPromptBuilder:
    def __init__(self, base_path="Eco.AI.Promts", output_dir="Builds"):
        self.base_path = base_path
        self.output_path = os.path.join(base_path, output_dir)
        # Создаем директорию для сборок, если её нет
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

    def build(self, agent_file):
        """
        Собирает агентский промпт на основе метаданных из папки Agents/
        """
        agent_full_path = os.path.join(self.base_path, "Agents", agent_file)
        
        if not os.path.exists(agent_full_path):
            raise FileNotFoundError(f"Файл агента не найден: {agent_full_path}")

        # 1. Загружаем рецепт агента (Frontmatter)
        agent_recipe = frontmatter.load(agent_full_path)
        
        # Извлекаем параметры из метаданных агента
        model = agent_recipe.get("model", "gpt-4")
        temp = agent_recipe.get("temperature", 0.2)
        assembly = agent_recipe.get("assembly", [])

        # 2. Собираем содержимое всех указанных модулей
        assembled_content = []
        for rel_path in assembly:
            full_module_path = os.path.join(self.base_path, rel_path)
            
            if os.path.exists(full_module_path):
                module = frontmatter.load(full_module_path)
                # Добавляем заголовок для отладки в итоговом файле
                header = f"/* --- MODULE: {rel_path} --- */"
                assembled_content.append(f"{header}\n{module.content.strip()}")
            else:
                print(f" ПРЕДУПРЕЖДЕНИЕ: Модуль {rel_path} не найден.")

        # 3. Формируем финальный текст
        final_prompt_text = "\n\n".join(assembled_content)

        # 4. Сохраняем результат в файл
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        agent_name = os.path.splitext(agent_file)[0]
        file_name = f"build_{agent_name}_{timestamp}.txt"
        save_path = os.path.join(self.output_path, file_name)

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(f"// AGENT: {agent_name}\n")
            f.write(f"// MODEL: {model}\n")
            f.write(f"// TEMPERATURE: {temp}\n")
            f.write("// " + "="*50 + "\n\n")
            f.write(final_prompt_text)

        return {
            "text": final_prompt_text,
            "model": model,
            "temp": temp,
            "save_path": save_path
        }

# --- ПРИМЕР ИСПОЛЬЗОВАНИЯ ---
if __name__ == "__main__":
    # Инициализация сборщика (базовый путь — текущая директория)
    builder = EcoPromptBuilder(base_path=".")

    # Получаем список агентов из аргументов командной строки
    # sys.argv[0] - это имя самого скрипта, поэтому берем со следующего
    args = sys.argv[1:]

    if not args:
        print("Использование: python3 builder.py <agent_file1.md> <agent_file2.md> ...")
        print("Попытка сборки всех агентов по умолчанию из папки Agents/...")
        # Автоматический поиск всех .md файлов в папке Agents
        agents_dir = os.path.join(".", "Agents")
        if os.path.exists(agents_dir):
            args = [f for f in os.listdir(agents_dir) if f.endswith(".md")]
        else:
            print(f"[Ошибка] Папка {agents_dir} не найдена.")
            sys.exit(1)

    print(f"--- Запуск сборки Eco AI Агентов (Всего: {len(args)}) ---")
    print("-" * 40)

    for agent_file in args:
        try:
            # Сборка конкретного агента
            result = builder.build(agent_file)
            
            print(f"[Успех] Агент: {agent_file}")
            print(f"  └─ Файл: {result['save_path']}")
            print(f"  └─ Модель: {result['model']} | Temp: {result['temp']}")
            print("-" * 40)

        except FileNotFoundError:
            print(f"[Пропуск] Файл Agents/{agent_file} не найден.")
        except Exception as e:
            print(f"[Ошибка] Не удалось собрать {agent_file}: {e}")

    print("\nГотово. Результаты в папке ./Builds/")
