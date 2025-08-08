#!/usr/bin/env python3
"""
Debug Log Cleanup Script
디버깅 로그를 정리하는 스크립트
"""

import os
import re

def cleanup_js_debug_logs(file_path):
    """JavaScript 파일의 디버깅 로그를 조건부로 변경"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 🔴 CRITICAL DEBUG 로그들을 조건부 로그로 변경
    patterns = [
        (r"console\.log\('🔴 CRITICAL DEBUG:(.*?)'\);", r"if (this.debug) console.log('DEBUG:\1');"),
        (r'console\.log\("🔴 CRITICAL DEBUG:(.*?)"\);', r'if (this.debug) console.log("DEBUG:\1");'),
        (r"console\.log\('🔴 WARNING:(.*?)'\);", r"if (this.debug) console.log('WARNING:\1');"),
        (r"console\.log\('🔴 STARTING POLLING(.*?)'\);", r"if (this.debug) console.log('POLLING:\1');"),
        (r"console\.log\('🔴 STOPPING POLLING(.*?)'\);", r"if (this.debug) console.log('POLLING:\1');"),
        (r"console\.log\('🔴 ✅ POLLING STOPPED'\);", r"if (this.debug) console.log('POLLING: Stopped');"),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Cleaned up debug logs in {file_path}")

def cleanup_python_debug_logs(file_path):
    """Python 파일의 디버깅 로그를 조건부로 변경"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 🔴 CRITICAL DEBUG 로그들을 조건부 로그로 변경
    patterns = [
        (r'print\(f"\[🔴 CRITICAL DEBUG\](.*?)"\)', r'if os.getenv("DEBUG_MODE"): print(f"[DEBUG]\1")'),
        (r"print\(f'\[🔴 CRITICAL DEBUG\](.*?)'\)", r"if os.getenv('DEBUG_MODE'): print(f'[DEBUG]\1')"),
        (r'print\("\[🔴 CRITICAL DEBUG\](.*?)"\)', r'if os.getenv("DEBUG_MODE"): print("[DEBUG]\1")'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Cleaned up debug logs in {file_path}")

def main():
    """메인 실행 함수"""
    base_dir = os.path.dirname(__file__)
    
    # JavaScript 파일 정리
    js_file = os.path.join(base_dir, 'web', 'static', 'js', 'app.js')
    if os.path.exists(js_file):
        cleanup_js_debug_logs(js_file)
    
    # Python 파일 정리  
    python_file = os.path.join(base_dir, 'web', 'app.py')
    if os.path.exists(python_file):
        cleanup_python_debug_logs(python_file)
    
    print("\n🎉 디버깅 로그 정리가 완료되었습니다!")
    print("📝 이제 디버깅 로그는 개발 환경에서만 표시됩니다:")
    print("   - JavaScript: localhost에서만 표시")
    print("   - Python: DEBUG_MODE=true 환경변수 설정 시만 표시")

if __name__ == "__main__":
    main()