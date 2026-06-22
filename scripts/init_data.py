"""
최초 1회 실행: 현재 공고 목록을 '기존 데이터'로 저장하여
이후 실제 신규 공고만 알림이 오도록 초기화합니다.

사용법:
  python scripts/init_data.py
"""

import json
import sys
from pathlib import Path

# monitor.py의 함수 재사용
sys.path.insert(0, str(Path(__file__).parent))
from monitor import TARGETS, fetch_all_first_page, save_items


def main():
    print("PIMAC 공고 데이터 초기화 시작\n")
    for key, cfg in TARGETS.items():
        label = cfg["label"]
        url = cfg["url"]
        data_file = cfg["data_file"]

        print(f"  {label} 크롤링 중...")
        items = fetch_all_first_page(url)
        if items:
            save_items(data_file, items)
            print(f"  → {len(items)}건 저장: {data_file}\n")
        else:
            print(f"  → 항목을 가져오지 못했습니다.\n")

    print("초기화 완료. data/ 폴더를 git add 후 push 하세요.")


if __name__ == "__main__":
    main()
