# 2026년 2차 서울시 청년안심주택(공공임대) 청약 도우미

66페이지 분량의 입주자모집공고문을 직접 읽지 않아도, 자연어 질문 한 번으로 일정·자격·임대조건·서류·가점 등 원하는 정보를 찾아주는 RAG 및 Text2SQL 기반 챗봇 시스템입니다.

---

## 1. 프로젝트 기획

### 기획 배경 및 필요성

* **방대한 문서 분량**: 66페이지에 달하는 공고문 내에 60개 이상의 단지 정보와 복잡한 표 데이터 혼재
* **정보 분산**: 일정, 자격요건, 단지별 임대조건, 가점, 제출서류 등이 서로 다른 장(章)에 분산
* **복잡한 자격 판정**: 나이·소득·자산·순위·가점이 조건문과 표로 얽혀 있어 지원자 스스로 계산하기 어려움
* **신청 오류 방지**: 접수 후 수정이 불가하며 자격 미숙지로 인한 불이익을 방지하기 위해 공고문 근거 기반 질의응답 시스템 필요

### 핵심 기능

* **청약 일정 및 자격 안내**: 접수 일정, 계층별(청년/신혼부부) 신청 자격 및 순위 확인
* **단지별 임대조건 조회**: 단지명 및 평형별 보증금, 계약금, 잔금, 월 임대료 확인
* **가점 및 서류 안내**: 서울 거주 기간, 청약통장 납입 횟수 기반 가점 계산 및 순위별 필수 제출 서류 목록 제공
* **근거 기반 답변**: 답변 생성 시 참고한 공고문 페이지 번호와 카테고리를 함께 제시하여 신뢰성 확보

---

## 2. 사용 데이터 설명

프로젝트 데이터는 질의 특성에 따라 비정형 문서 데이터(PDF)와 정형 데이터(CSV/DB)로 나누어 구성했습니다.

### 비정형 데이터 (PDF 공고문)

* **파일명**: `2026년 2차 청년안심주택 모집공고문.pdf` (서울주택도시공사, 2026.07.31. 공고, 68페이지)
* **전처리 및 청킹**:
* `PyMuPDF(fitz)`로 페이지 단위 텍스트 추출
* `RecursiveCharacterTextSplitter`를 사용해 500자 단위 청킹 (50자 오버랩, 총 363개 청크 생성)


* **메타데이터 및 벡터 저장**:
* 공고문 목차(1~14장) 기준 12개 카테고리(공급일정, 신청자격, 임대조건, 제출서류 등) 메타데이터 태깅
* OpenAI `text-embedding-3-small` 임베딩 적용 후 `Qdrant Cloud`에 적재하여 카테고리 필터링 지원



### 정형 데이터 (CSV 3종)

수치 비교, 정렬, 필터링이 필요한 데이터는 정형화하여 `SQLite` 및 `Supabase(PostgreSQL)`에 적재 후 Text2SQL로 연동했습니다.

| CSV 파일명 | 주요 내용 |
| --- | --- |
| **`apartment.csv`** | 단지별 공급유형, 평면, 공급호수, 임대보증금, 계약금, 잔금, 월임대료, 시공사 정보 |
| **`preferences.csv`** | 청년/신혼부부Ⅰ/신혼부부Ⅱ 계층별 신청자격, 순위, 소득·자산 기준, 가점 배점표 |
| **`service_center.csv`** | 공공임대·민간임대·법률지원 등 유형별 문의처 및 연락처 |

---

## 3. 웹 서비스 구조

기존 LangGraph 워크플로를 그대로 재사용하고, 그 위에 API 서버와 React 웹 UI를 얹었습니다.

```
브라우저 (React + Vite + Tailwind CSS)
   │  POST /api/chat/stream  (SSE)
   ▼
FastAPI (src/api/main.py)
   │  graph.astream(stream_mode=["updates", "messages"])
   ▼
LangGraph (src/ai/graph.py)
   ├─ classify_intent ─┬─ general_answer
   │                   ├─ vector_search   → Qdrant Cloud  (+ rewrite_query 재시도)
   │                   └─ database_query  → Supabase(PostgreSQL) Text2SQL
   └─ generate_answer  → 최종 답변
```

### 디렉터리

| 경로 | 설명 |
| --- | --- |
| `src/ai/` | LangGraph 워크플로 (기존 코드, 수정 없음) |
| `src/api/main.py` | FastAPI 서버 · SSE 스트리밍 · 공고문 PDF 제공 |
| `web/` | React(Vite) + Tailwind CSS 프론트엔드 |
| `src/demo/streamlit_example.py` | 기존 Streamlit 데모 (그대로 유지) |

### 웹 UI 주요 기능

* **실시간 스트리밍**: 답변 토큰을 그대로 흘려보내고, LangGraph가 거쳐 가는 노드(의도 분류 → 벡터 검색 → 답변 생성)를 진행 중에 표시
* **근거 공개**: 답변마다 분류된 의도, 검색된 공고문 청크(카테고리·페이지), 실행된 SQL과 조회 결과를 펼쳐볼 수 있음
* **원문 링크**: 근거 문서의 페이지 번호를 누르면 공고문 PDF의 해당 쪽이 열림
* **멀티턴 대화**: 이전 대화 맥락을 함께 전송해 "그럼 보증금은?" 같은 후속 질문 처리
* **예시 질문 · 연결 상태**: 사이드바에서 의도별 예시 질문을 클릭해 바로 질의, 환경 변수 설정 상태 확인

### API 엔드포인트

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/api/health` | 필수 환경 변수 설정 여부 |
| `GET` | `/api/examples` | 의도별 예시 질문 목록 |
| `GET` | `/api/notice.pdf` | 모집공고문 원본 PDF |
| `POST` | `/api/chat` | 단발 응답 (비스트리밍) |
| `POST` | `/api/chat/stream` | SSE 스트리밍 (`start`/`node`/`intent`/`token`/`meta`/`done`/`error` 이벤트) |

---

## 4. 실행 방법

### 사전 준비

`.env.example`을 복사해 `.env`를 만들고 값을 채웁니다.

```bash
cp .env.example .env
```

| 변수 | 용도 |
| --- | --- |
| `OPENAI_API_KEY` | 임베딩(`text-embedding-3-small`) 및 답변 생성 |
| `QDRANT_URL`, `QDRANT_API_KEY` | Qdrant Cloud 벡터 검색 |
| `SUPABASE_DB_URL` | Supabase(PostgreSQL) Text2SQL 조회 |

### 개발 모드 (터미널 2개)

```bash
# 1) 의존성 설치
uv sync
cd web && npm install && cd ..

# 2) API 서버 (터미널 A)
uv run uvicorn api.main:app --app-dir src --reload --port 8000

# 3) 웹 프론트엔드 (터미널 B)
cd web && npm run dev
```

브라우저에서 <http://localhost:5173> 으로 접속합니다.
Vite dev 서버가 `/api` 요청을 8000 포트로 프록시하므로 별도 설정이 필요 없습니다.

### 프로덕션 모드 (서버 1개)

프론트엔드를 빌드해 두면 FastAPI가 `web/dist`를 함께 서빙합니다.

```bash
cd web && npm run build && cd ..
uv run uvicorn api.main:app --app-dir src --port 8000
```

브라우저에서 <http://localhost:8000> 으로 접속합니다.

### Streamlit 데모 (기존)

```bash
uv run streamlit run src/demo/streamlit_example.py
```
