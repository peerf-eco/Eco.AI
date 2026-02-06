#!/usr/bin/env python3
"""
Анализ токенов в файлах rag_storage

Подсчитывает количество токенов для каждого файла, чтобы определить
требования к модели эмбеддингов.

Использует tiktoken для точного подсчета токенов по модели text-embedding-3-small
(стандартная модель для эмбеддингов OpenAI).
"""

import os
import json
import statistics
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

try:
    import tiktoken
except ImportError:
    print("[ERROR] tiktoken not installed. Install with: pip install tiktoken")
    exit(1)


# Расширения файлов для анализа
CODE_EXTENSIONS = {'.h', '.hpp', '.c', '.cpp'}

# Модели для анализа (можно добавить другие)
EMBEDDING_MODELS = {
    'text-embedding-3-small': 'cl100k_base',  # 1536 dimensions
    'text-embedding-3-large': 'cl100k_base',   # 3072 dimensions
    'text-embedding-ada-002': 'cl100k_base',   # 1536 dimensions
}


def count_tokens(text: str, encoding_name: str) -> int:
    """Подсчитать токены в тексте"""
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))


def analyze_file(file_path: Path, encodings: Dict[str, str]) -> Dict[str, any]:
    """Анализировать один файл"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        file_stats = {
            'path': str(file_path),
            'size_bytes': os.path.getsize(file_path),
            'size_chars': len(content),
            'size_lines': len(content.splitlines()),
            'tokens': {}
        }
        
        # Подсчет токенов для каждой модели
        for model_name, encoding_name in encodings.items():
            token_count = count_tokens(content, encoding_name)
            file_stats['tokens'][model_name] = token_count
        
        return file_stats
    
    except Exception as e:
        print(f"[WARNING] Failed to analyze {file_path}: {e}")
        return None


def analyze_directory(root_dir: Path, encodings: Dict[str, str]) -> List[Dict]:
    """Анализировать все файлы в директории"""
    results = []
    
    print(f"[INFO] Scanning directory: {root_dir}")
    print(f"[INFO] Looking for files with extensions: {', '.join(CODE_EXTENSIONS)}")
    print()
    
    file_count = 0
    for file_path in root_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in CODE_EXTENSIONS:
            file_count += 1
            if file_count % 10 == 0:
                print(f"[INFO] Processed {file_count} files...", end='\r')
            
            stats = analyze_file(file_path, encodings)
            if stats:
                results.append(stats)
    
    print(f"[INFO] Processed {file_count} files total")
    print()
    
    return results


def calculate_statistics(results: List[Dict], model_name: str) -> Dict:
    """Вычислить статистику для конкретной модели"""
    token_counts = [r['tokens'][model_name] for r in results]
    
    if not token_counts:
        return None
    
    return {
        'model': model_name,
        'total_files': len(token_counts),
        'total_tokens': sum(token_counts),
        'min_tokens': min(token_counts),
        'max_tokens': max(token_counts),
        'mean_tokens': statistics.mean(token_counts),
        'median_tokens': statistics.median(token_counts),
        'stdev_tokens': statistics.stdev(token_counts) if len(token_counts) > 1 else 0,
    }


def print_statistics(stats: Dict, model_name: str):
    """Вывести статистику в консоль"""
    print(f"\n{'='*70}")
    print(f"  STATISTICS for {model_name}")
    print(f"{'='*70}")
    print(f"Total files analyzed:     {stats['total_files']}")
    print(f"Total tokens:             {stats['total_tokens']:,}")
    print(f"Min tokens per file:     {stats['min_tokens']:,}")
    print(f"Max tokens per file:     {stats['max_tokens']:,}")
    print(f"Mean tokens per file:    {stats['mean_tokens']:,.1f}")
    print(f"Median tokens per file:  {stats['median_tokens']:,.1f}")
    print(f"Std deviation:           {stats['stdev_tokens']:,.1f}")
    print()


def find_extreme_files(results: List[Dict], model_name: str, count: int = 5):
    """Найти файлы с минимальным и максимальным количеством токенов"""
    sorted_results = sorted(
        results,
        key=lambda x: x['tokens'][model_name]
    )
    
    print(f"\n{'='*70}")
    print(f"  TOP {count} SMALLEST FILES ({model_name})")
    print(f"{'='*70}")
    for i, result in enumerate(sorted_results[:count], 1):
        tokens = result['tokens'][model_name]
        rel_path = result['path'].replace(os.getcwd() + os.sep, '')
        print(f"{i}. {tokens:>6,} tokens - {rel_path}")
    
    print(f"\n{'='*70}")
    print(f"  TOP {count} LARGEST FILES ({model_name})")
    print(f"{'='*70}")
    for i, result in enumerate(sorted_results[-count:], 1):
        tokens = result['tokens'][model_name]
        rel_path = result['path'].replace(os.getcwd() + os.sep, '')
        print(f"{i}. {tokens:>6,} tokens - {rel_path}")


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze token counts in rag_storage files'
    )
    parser.add_argument(
        '--dir',
        type=str,
        default='rag_storage',
        help='Directory to analyze (default: rag_storage)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='text-embedding-3-small',
        choices=list(EMBEDDING_MODELS.keys()),
        help='Embedding model to use for token counting (default: text-embedding-3-small)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output JSON file for detailed results'
    )
    parser.add_argument(
        '--all-models',
        action='store_true',
        help='Analyze for all available models'
    )
    
    args = parser.parse_args()
    
    # Определить модели для анализа
    if args.all_models:
        models_to_analyze = EMBEDDING_MODELS
    else:
        models_to_analyze = {args.model: EMBEDDING_MODELS[args.model]}
    
    # Проверить директорию
    root_dir = Path(args.dir)
    if not root_dir.exists():
        print(f"[ERROR] Directory not found: {root_dir}")
        exit(1)
    
    print(f"[INFO] Starting token analysis...")
    print(f"[INFO] Root directory: {root_dir.absolute()}")
    print(f"[INFO] Models to analyze: {', '.join(models_to_analyze.keys())}")
    print()
    
    # Анализ файлов
    results = analyze_directory(root_dir, models_to_analyze)
    
    if not results:
        print("[ERROR] No files found to analyze")
        exit(1)
    
    # Вычислить статистику для каждой модели
    all_stats = {}
    for model_name in models_to_analyze.keys():
        stats = calculate_statistics(results, model_name)
        if stats:
            all_stats[model_name] = stats
            print_statistics(stats, model_name)
            find_extreme_files(results, model_name, count=5)
    
    # Сохранить результаты в JSON
    if args.output:
        output_data = {
            'statistics': all_stats,
            'files': results
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\n[INFO] Detailed results saved to: {args.output}")
    
    # Рекомендации по выбору модели
    print(f"\n{'='*70}")
    print("  RECOMMENDATIONS")
    print(f"{'='*70}")
    
    if args.all_models:
        primary_model = 'text-embedding-3-small'
    else:
        primary_model = args.model
    
    stats = all_stats[primary_model]
    
    print(f"\nFor {primary_model}:")
    print(f"  - Max file size: {stats['max_tokens']:,} tokens")
    
    # Проверить лимиты моделей
    max_context_sizes = {
        'text-embedding-3-small': 8191,  # Максимум токенов для одного запроса
        'text-embedding-3-large': 8191,
        'text-embedding-ada-002': 8191,
    }
    
    max_context = max_context_sizes.get(primary_model, 8191)
    
    if stats['max_tokens'] > max_context:
        print(f"  [WARNING] Some files exceed model context limit ({max_context:,} tokens)")
        print(f"            You may need to chunk large files before embedding")
    else:
        print(f"  [OK] All files fit within model context limit ({max_context:,} tokens)")
    
    print(f"\n  Recommended chunk size for RAG: {int(stats['mean_tokens'] * 0.8):,} tokens")
    print(f"  Recommended chunk overlap: {int(stats['mean_tokens'] * 0.1):,} tokens")


if __name__ == '__main__':
    main()

