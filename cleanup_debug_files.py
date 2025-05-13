#!/usr/bin/env python
"""
템플릿 디버그 파일을 정리하는 스크립트.
특정 패턴의 파일을 지정된 디렉토리로 이동하거나 삭제합니다.
"""

import os
import shutil
import argparse
from pathlib import Path
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="Clean up template debug files")
    parser.add_argument(
        "--action", 
        choices=["move", "delete"], 
        default="move",
        help="Action to perform on debug files"
    )
    parser.add_argument(
        "--target-dir", 
        default="debug_archives",
        help="Directory to move files to (when action is 'move')"
    )
    parser.add_argument(
        "--pattern", 
        default="template_debug_",
        help="File pattern to match for cleanup"
    )
    
    args = parser.parse_args()
    
    # 현재 디렉토리 내의 모든 파일 가져오기
    files = [f for f in os.listdir() if os.path.isfile(f)]
    
    # 패턴과 일치하는 파일 필터링
    debug_files = [f for f in files if args.pattern in f]
    
    if not debug_files:
        print(f"No files matching pattern '{args.pattern}' found.")
        return
    
    print(f"Found {len(debug_files)} debug files.")
    
    if args.action == "move":
        # 대상 디렉토리 생성 (없는 경우)
        target_dir = Path(args.target_dir)
        if not target_dir.exists():
            target_dir.mkdir(parents=True)
            print(f"Created directory: {target_dir}")
        
        # 현재 날짜로 하위 디렉토리 생성
        date_dir = target_dir / datetime.now().strftime("%Y%m%d")
        if not date_dir.exists():
            date_dir.mkdir(parents=True)
        
        # 파일 이동
        for file in debug_files:
            src = Path(file)
            dst = date_dir / src.name
            shutil.move(str(src), str(dst))
        
        print(f"Moved {len(debug_files)} files to {date_dir}")
    
    else:  # delete
        for file in debug_files:
            os.remove(file)
        print(f"Deleted {len(debug_files)} files")

if __name__ == "__main__":
    main() 