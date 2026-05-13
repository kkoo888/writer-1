#!/usr/bin/env python3
"""
中文字数统计工具
用法:
  python3 word_count.py "正文/第一章·末日第一天.md"  # 统计单个文件
  python3 word_count.py --all                          # 统计所有章节
  python3 word_count.py --dir "正文/"                  # 统计指定目录
  python3 word_count.py --json                         # JSON 输出
"""

import re
import sys
import json
import os
import glob
from pathlib import Path


def count_chinese_words(text: str) -> dict:
    """统计中文字数"""
    # 移除 markdown 标记（标题符号、链接等）
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'[*_`~]', '', text)
    
    # 中文字符（包含 CJK 统一汉字）
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', text))
    
    # 中文标点
    chinese_punctuation = len(re.findall(r'[\u3000-\u303f\uff00-\uffef\u2000-\u206f]', text))
    
    # 英文单词（连续字母串）
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    
    # 数字串
    numbers = len(re.findall(r'\d+', text))
    
    total = chinese_chars + chinese_punctuation + english_words + numbers
    
    return {
        'chinese_chars': chinese_chars,
        'chinese_punctuation': chinese_punctuation,
        'english_words': english_words,
        'numbers': numbers,
        'total': total
    }


def count_file(filepath: str, target: int = 2300, tolerance: float = 0.1) -> dict:
    """统计单个文件字数"""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    stats = count_chinese_words(text)
    
    lower = int(target * (1 - tolerance))
    upper = int(target * (1 + tolerance))
    
    if stats['total'] < lower:
        status = 'under'
        deviation = f"-{(1 - stats['total']/target)*100:.1f}%"
    elif stats['total'] > upper:
        status = 'over'
        deviation = f"+{(stats['total']/target - 1)*100:.1f}%"
    else:
        status = 'pass'
        deviation = f"{(stats['total']/target - 1)*100:+.1f}%"
    
    return {
        'file': os.path.basename(filepath),
        'path': filepath,
        **stats,
        'target': target,
        'tolerance': f"±{int(tolerance*100)}%",
        'range': [lower, upper],
        'status': status,
        'deviation': deviation
    }


def count_directory(directory: str, target: int = 2300, tolerance: float = 0.1) -> dict:
    """统计目录下所有章节"""
    files = sorted(glob.glob(os.path.join(directory, "*.md")))
    
    if not files:
        return {'error': f'No .md files found in {directory}'}
    
    chapters = []
    total_words = 0
    
    for f in files:
        result = count_file(f, target, tolerance)
        chapters.append(result)
        total_words += result['total']
    
    avg = total_words // len(chapters) if chapters else 0
    all_pass = all(c['status'] == 'pass' for c in chapters)
    
    return {
        'total_chapters': len(chapters),
        'total_words': total_words,
        'average_per_chapter': avg,
        'target': target,
        'all_within_tolerance': all_pass,
        'chapters': chapters
    }


def main():
    args = sys.argv[1:]
    
    if not args:
        print("用法:")
        print('  python3 word_count.py "正文/第一章·末日第一天.md"')
        print("  python3 word_count.py --all")
        print('  python3 word_count.py --dir "正文/"')
        print("  python3 word_count.py --json")
        sys.exit(1)
    
    json_output = '--json' in args
    target = 2300
    tolerance = 0.1
    
    # 检查自定义目标
    for i, arg in enumerate(args):
        if arg == '--target' and i + 1 < len(args):
            target = int(args[i + 1])
        if arg == '--tolerance' and i + 1 < len(args):
            tolerance = float(args[i + 1])
    
    if '--all' in args:
        # 统计所有章节（搜索常见目录）
        search_dirs = ["正文/", "末日求生/末日求生/正文/", "*/正文/"]
        result = None
        for d in search_dirs:
            if os.path.isdir(d):
                result = count_directory(d, target, tolerance)
                break
            # 通配符展开
            import glob as g
            matches = g.glob(d)
            if matches and os.path.isdir(matches[0]):
                result = count_directory(matches[0], target, tolerance)
                break
        
        if result is None:
            result = {'error': '未找到正文目录', 'total_chapters': 0, 'total_words': 0, 'average_per_chapter': 0, 'all_within_tolerance': False, 'chapters': []}
        if json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\n📊 字数统计报告")
            print(f"{'='*50}")
            print(f"总章数: {result['total_chapters']}")
            print(f"总字数: {result['total_words']:,}")
            print(f"平均每章: {result['average_per_chapter']:,}")
            print(f"目标: {target} ±{int(tolerance*100)}%")
            print(f"全部达标: {'✅' if result['all_within_tolerance'] else '❌'}")
            print(f"\n{'章节':<30} {'字数':>8} {'状态':>6} {'偏差':>8}")
            print(f"{'-'*55}")
            for ch in result['chapters']:
                status_icon = '✅' if ch['status'] == 'pass' else '❌'
                print(f"{ch['file']:<30} {ch['total']:>8,} {status_icon:>6} {ch['deviation']:>8}")
    
    elif '--dir' in args:
        idx = args.index('--dir')
        if idx + 1 < len(args):
            directory = args[idx + 1]
            result = count_directory(directory, target, tolerance)
            if json_output:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"\n📊 目录: {directory}")
                print(f"总字数: {result['total_words']:,}")
        else:
            print("错误: --dir 需要指定目录")
            sys.exit(1)
    
    else:
        # 统计单个文件
        filepath = args[0]
        if not os.path.exists(filepath):
            print(f"错误: 文件不存在 - {filepath}")
            sys.exit(1)
        
        result = count_file(filepath, target, tolerance)
        if json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\n📊 字数统计: {result['file']}")
            print(f"{'='*40}")
            print(f"中文字符: {result['chinese_chars']:,}")
            print(f"中文标点: {result['chinese_punctuation']:,}")
            print(f"英文单词: {result['english_words']:,}")
            print(f"数字串: {result['numbers']:,}")
            print(f"{'─'*30}")
            print(f"总字数: {result['total']:,}")
            print(f"目标: {result['target']} {result['tolerance']}")
            print(f"范围: {result['range'][0]:,} - {result['range'][1]:,}")
            status_icon = '✅' if result['status'] == 'pass' else '❌'
            print(f"状态: {status_icon} {result['status']} ({result['deviation']})")


if __name__ == '__main__':
    main()
