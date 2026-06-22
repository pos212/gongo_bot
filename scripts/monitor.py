"""
PIMAC 공고 모니터링 스크립트
- 제3자 제안공고: https://pimac.kdi.re.kr/notice/accept_list.jsp
- 시설사업기본계획 고시: https://pimac.kdi.re.kr/notice/notification_list.jsp
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── 설정 ────────────────────────────────────────────────────────────────────
TARGETS = {
    "third_party": {
        "label": "📋 제3자 제안공고",
        "url": "https://pimac.kdi.re.kr/notice/accept_list.jsp",
        "data_file": Path("data/third_party.json"),
    },
    "basic_plan": {
        "label": "📢 시설사업기본계획 고시",
        "url": "https://pimac.kdi.re.kr/notice/notification_list.jsp",
        "data_file": Path("data/basic_plan.json"),
    },
}

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://pimac.kdi.re.kr/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ── 크롤링 ───────────────────────────────────────────────────────────────────
def fetch_page(url: str, page: int = 1) -> BeautifulSoup:
    """페이지 HTML을 가져와 BeautifulSoup 객체로 반환."""
    params = {"pageIndex": page}
    resp = SESSION.get(url, params=params, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return BeautifulSoup(resp.text, "html.parser")


def parse_rows(soup: BeautifulSoup) -> list[dict]:
    """
    공통 테이블 파싱.
    PIMAC 목록 페이지는 <table class='board_list'> 또는 <table> 안에
    <tbody><tr> 구조로 되어 있음.
    """
    items = []
    table = soup.find("table", class_=lambda c: c and "board" in c.lower())
    if not table:
        table = soup.find("table")
    if not table:
        return items

    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody else table.find_all("tr")

    for row in rows:
        cols = row.find_all("td")
        if not cols or len(cols) < 2:
            continue

        # 번호 / 제목 / 날짜 추출 (열 개수에 따라 유연하게)
        num_text = cols[0].get_text(strip=True)
        if not num_text or num_text in ("번호", "No"):
            continue  # 헤더행 skip

        title_tag = row.find("a")
        title = title_tag.get_text(strip=True) if title_tag else cols[1].get_text(strip=True)

        # onclick 또는 href에서 링크 추출
        href = ""
        if title_tag:
            href = title_tag.get("href", "")
            onclick = title_tag.get("onclick", "")
            if not href and onclick:
                # ex) goView('12345') → /notice/accept_view.jsp?idx=12345
                import re
                m = re.search(r"'(\d+)'", onclick)
                if m:
                    href = f"?idx={m.group(1)}"

        # 날짜: 보통 마지막 또는 마지막에서 두 번째 열
        date_text = cols[-1].get_text(strip=True)

        items.append(
            {
                "num": num_text,
                "title": title,
                "href": href,
                "date": date_text,
            }
        )

    return items


def fetch_all_first_page(url: str) -> list[dict]:
    """첫 페이지 공고 목록을 반환."""
    try:
        soup = fetch_page(url, page=1)
        rows = parse_rows(soup)
        return rows
    except Exception as e:
        print(f"[ERROR] 크롤링 실패 ({url}): {e}", file=sys.stderr)
        return []


# ── 데이터 저장/로드 ─────────────────────────────────────────────────────────
def load_saved(path: Path) -> dict[str, dict]:
    """저장된 공고 목록 로드. key = num(번호)."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {item["num"]: item for item in data}
    except Exception:
        return {}


def save_items(path: Path, items: list[dict]) -> None:
    """공고 목록을 JSON으로 저장."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


# ── 텔레그램 ─────────────────────────────────────────────────────────────────
def send_telegram(message: str) -> bool:
    """텔레그램 메시지 전송."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] 텔레그램 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        return False

    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(api_url, json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] 텔레그램 전송 실패: {e}", file=sys.stderr)
        return False


def build_message(label: str, new_items: list[dict], base_url: str) -> str:
    """신규 공고 알림 메시지 생성."""
    lines = [
        f"<b>{label}</b>",
        f"신규 공고 {len(new_items)}건이 등록되었습니다.",
        "",
    ]
    for item in new_items[:10]:  # 최대 10건
        link = item["href"]
        if link and not link.startswith("http"):
            from urllib.parse import urljoin
            link = urljoin(base_url, link)
        title_line = f"• [{item['date']}] {item['title']}"
        if link:
            title_line = f'• [{item["date"]}] <a href="{link}">{item["title"]}</a>'
        lines.append(title_line)

    if len(new_items) > 10:
        lines.append(f"... 외 {len(new_items) - 10}건")

    lines.append("")
    lines.append(f"🔗 <a href='{base_url}'>PIMAC 바로가기</a>")
    return "\n".join(lines)


# ── 메인 ─────────────────────────────────────────────────────────────────────
def run() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] PIMAC 공고 모니터링 시작")

    all_new: list[tuple[str, list[dict], str]] = []  # (label, new_items, base_url)

    for key, cfg in TARGETS.items():
        label = cfg["label"]
        url = cfg["url"]
        data_file = cfg["data_file"]

        print(f"  → {label} 크롤링 중...")
        current_items = fetch_all_first_page(url)
        if not current_items:
            print(f"     [WARN] 항목을 가져오지 못했습니다.")
            continue

        saved = load_saved(data_file)
        current_nums = {item["num"] for item in current_items}
        new_items = [item for item in current_items if item["num"] not in saved]

        print(f"     현재 {len(current_items)}건 / 신규 {len(new_items)}건")

        # 데이터 업데이트: 기존 + 신규 병합 (번호 기준 dedup)
        merged = {**saved, **{item["num"]: item for item in current_items}}
        save_items(data_file, list(merged.values()))

        if new_items:
            all_new.append((label, new_items, url))

        time.sleep(2)  # 서버 부하 방지

    # 알림 전송
    if all_new:
        for label, new_items, url in all_new:
            msg = build_message(label, new_items, url)
            print(f"\n  📨 텔레그램 전송: {label} ({len(new_items)}건)")
            send_telegram(msg)
            time.sleep(1)
    else:
        print("  ✅ 신규 공고 없음")

    print("모니터링 완료.")


if __name__ == "__main__":
    run()
