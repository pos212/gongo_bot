# PIMAC 공고 모니터링

PIMAC(KDI 공공투자관리센터) 민간투자 공고를 매일 오전 7시에 자동으로 확인하고,
신규 공고가 있으면 텔레그램으로 알려주는 GitHub Actions 봇입니다.

## 모니터링 대상

| 구분 | URL |
|---|---|
| 제3자 제안공고 | https://pimac.kdi.re.kr/notice/accept_list.jsp |
| 시설사업기본계획 고시 | https://pimac.kdi.re.kr/notice/notification_list.jsp |

---

## 설치 방법

### 1. 리포지토리 생성

이 폴더를 GitHub에 새 레포로 push 합니다.

```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/<your-id>/<repo-name>.git
git push -u origin main
```

### 2. 텔레그램 봇 준비

1. [@BotFather](https://t.me/botfather) 에게 `/newbot` 명령어로 봇 생성
2. 발급받은 **Bot Token** 메모
3. 봇과 대화를 시작하거나 그룹에 추가한 뒤,  
   `https://api.telegram.org/bot<TOKEN>/getUpdates` 로 **chat_id** 확인

### 3. GitHub Secrets 등록

리포지토리 → **Settings → Secrets and variables → Actions → New repository secret**

| Secret 이름 | 값 |
|---|---|
| `TELEGRAM_TOKEN` | 텔레그램 Bot Token |
| `TELEGRAM_CHAT_ID` | 알림 받을 Chat ID |

### 4. 데이터 초기화 (최초 1회)

로컬에서 실행하면 현재 공고를 "기존 데이터"로 저장해 두어
이후 **실제 신규 공고만** 알림이 옵니다.

```bash
pip install -r requirements.txt
python scripts/init_data.py
git add data/
git commit -m "chore: 초기 데이터 저장"
git push
```

> 초기화를 건너뛰면 첫 실행 시 현재 모든 공고가 신규로 인식되어 대량 알림이 발송됩니다.

---

## 파일 구조

```
.
├── .github/
│   └── workflows/
│       └── monitor.yml      # GitHub Actions 스케줄 설정
├── data/
│   ├── third_party.json     # 제3자 제안공고 저장 목록
│   └── basic_plan.json      # 시설사업기본계획 고시 저장 목록
├── scripts/
│   ├── monitor.py           # 메인 크롤링 + 알림 로직
│   └── init_data.py         # 최초 데이터 초기화 스크립트
├── requirements.txt
└── README.md
```

---

## 수동 실행

GitHub 리포지토리 → **Actions → PIMAC 공고 모니터링 → Run workflow**

`force_notify` 옵션을 `true` 로 설정하면 신규 공고가 없어도 테스트 메시지가 전송됩니다.

---

## 주의사항

- PIMAC 사이트 구조가 변경되면 `scripts/monitor.py`의 `parse_rows()` 함수를 수정해야 합니다.
- GitHub Actions 무료 플랜 기준 월 2,000분 제공. 이 봇은 1회 실행 시 약 1~2분 소요됩니다.
