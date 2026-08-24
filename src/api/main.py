"""
청년안심주택 청약 도우미 - 웹 API 서버

React(Vite) 프론트엔드가 사용하는 FastAPI 서버입니다.
기존 LangGraph 그래프(src/ai/graph.py)를 그대로 재사용하며,
SSE(Server-Sent Events)로 워크플로 진행 상황과 토큰을 실시간 전송합니다.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Literal, Optional

# 이 파일이 스크립트로 실행돼도 `ai` 패키지를 찾을 수 있도록 src 경로 추가
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

PROJECT_ROOT = SRC_DIR.parent

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from pydantic import BaseModel, Field

load_dotenv(PROJECT_ROOT / ".env")

from ai.graph import create_graph  # noqa: E402

# 공고문 원본 PDF (답변 근거 페이지 링크에 사용)
NOTICE_PDF = PROJECT_ROOT / "examples" / "공공_260731_2026년 2차 청년안심주택 모집공고문.pdf"

# 워크플로 노드 → 사용자에게 보여줄 라벨
NODE_LABELS: dict[str, str] = {
    "classify_intent": "질문 의도 분류",
    "general_answer": "일반 답변 생성",
    "vector_search": "공고문 벡터 검색 (Qdrant)",
    "rewrite_query": "검색 쿼리 재작성",
    "database_query": "Text2SQL 데이터베이스 조회",
    "generate_answer": "근거 기반 답변 생성",
}

# 최종 답변을 만드는 노드 (여기서 나오는 토큰만 화면에 흘려보냄)
ANSWER_NODES = {"generate_answer", "general_answer"}

REQUIRED_ENV = {
    "OPENAI_API_KEY": "OpenAI API",
    "QDRANT_URL": "Qdrant URL",
    "QDRANT_API_KEY": "Qdrant API Key",
    "SUPABASE_DB_URL": "Supabase DB",
}

EXAMPLE_QUESTIONS = [
    {
        "intent": "vector",
        "label": "공고문 검색",
        "items": [
            "청약 접수는 언제부터 언제까지인가요?",
            "청년 2순위로 신청하려면 어떤 서류가 필요한가요?",
            "반려동물을 키울 수 있나요?",
        ],
    },
    {
        "intent": "database",
        "label": "데이터 조회",
        "items": [
            "에이트플레이스 39A 타입 임대보증금과 월세는 얼마인가요?",
            "청년 1순위 자격요건에 해당하는 경우는 어떤 경우들이 있나요?",
            "민간임대 계약 관련해서 어디로 전화해야 하나요?",
        ],
    },
    {
        "intent": "general",
        "label": "일반 대화",
        "items": [
            "안녕하세요, 무엇을 도와줄 수 있나요?",
        ],
    },
]

app = FastAPI(title="청년안심주택 청약 도우미 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_graph = None


def get_graph():
    """그래프 lazy 초기화 (서버 기동 시점에 외부 연결을 강제하지 않기 위함)"""
    global _graph
    if _graph is None:
        _graph = create_graph()
    return _graph


# --------------------------------------------------------------------------
# 요청/응답 스키마
# --------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(
        ..., description="사용자/어시스턴트 대화 히스토리 (마지막은 user 메시지)"
    )


def to_langchain_messages(messages: list[ChatMessage]) -> list:
    """프론트엔드 대화 히스토리를 LangChain 메시지로 변환"""
    converted = []
    for message in messages:
        if message.role == "user":
            converted.append(HumanMessage(content=message.content))
        else:
            converted.append(AIMessage(content=message.content))
    return converted


def serialize_documents(documents: Optional[list]) -> list[dict[str, Any]]:
    """
    Qdrant 검색 결과(Document)를 JSON으로 직렬화.

    컬렉션에 동일한 청크가 중복 적재된 경우가 있어, 화면에 같은 근거가 여러 번
    노출되지 않도록 (페이지, 본문) 기준으로 중복을 제거합니다.
    """
    if not documents:
        return []

    serialized = []
    seen: set[tuple] = set()

    for document in documents:
        metadata = getattr(document, "metadata", {}) or {}
        content = getattr(document, "page_content", "")

        key = (metadata.get("page"), content)
        if key in seen:
            continue
        seen.add(key)

        serialized.append(
            {
                "content": content,
                "source": metadata.get("source"),
                "page": metadata.get("page"),
                "category": metadata.get("category"),
                "score": metadata.get("score"),
            }
        )
    return serialized


def build_meta(state: dict[str, Any]) -> dict[str, Any]:
    """그래프 최종 상태에서 프론트엔드가 표시할 워크플로 정보를 추출"""
    # database_query 노드는 성공한 첫 시도에도 retry_count를 1 올리므로
    # 실제 "재시도" 횟수로 환산해서 내려보냅니다.
    retry_count = state.get("retry_count") or 0
    if state.get("intent") == "database" and retry_count > 0:
        retry_count -= 1

    return {
        "intent": state.get("intent"),
        "retryCount": retry_count,
        "sqlQuery": state.get("sql_query"),
        "rewrittenQuery": state.get("rewritten_query"),
        "error": state.get("error"),
        "dbResults": state.get("db_results"),
        "documents": serialize_documents(state.get("vector_results")),
    }


def extract_answer(state: dict[str, Any]) -> str:
    """최종 상태의 마지막 메시지에서 답변 텍스트 추출"""
    messages = state.get("messages") or []
    if not messages:
        return "죄송합니다. 답변을 생성할 수 없습니다."

    last = messages[-1]
    content = getattr(last, "content", last)
    if isinstance(content, list):  # 멀티모달 형태 대비
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content)


def sse(event: str, data: dict[str, Any]) -> str:
    """SSE 프레임 문자열 생성"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# --------------------------------------------------------------------------
# 엔드포인트
# --------------------------------------------------------------------------


@app.get("/api/health")
async def health() -> dict[str, Any]:
    """환경 변수 설정 상태 확인 (프론트엔드 사이드바에 표시)"""
    env_status = [
        {"key": key, "label": label, "configured": bool(os.getenv(key))}
        for key, label in REQUIRED_ENV.items()
    ]
    return {
        "ok": all(item["configured"] for item in env_status),
        "env": env_status,
        "noticePdf": NOTICE_PDF.exists(),
    }


@app.get("/api/examples")
async def examples() -> dict[str, Any]:
    """예시 질문 목록"""
    return {"groups": EXAMPLE_QUESTIONS}


@app.get("/api/notice.pdf")
async def notice_pdf():
    """공고문 원본 PDF (근거 페이지 링크용)"""
    if not NOTICE_PDF.exists():
        return {"error": "공고문 PDF를 찾을 수 없습니다."}
    return FileResponse(
        NOTICE_PDF,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="notice.pdf"'},
    )


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    """비스트리밍 응답 (스트리밍 실패 시 폴백)"""
    graph = get_graph()
    state = await graph.ainvoke({"messages": to_langchain_messages(request.messages)})
    return {"answer": extract_answer(state), "meta": build_meta(state)}


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    SSE 스트리밍 응답

    이벤트 종류:
      - node   : 워크플로 노드 진입/완료
      - intent : 분류된 질문 의도
      - token  : 답변 토큰 (모델이 토큰 스트리밍을 지원할 때만)
      - meta   : 워크플로 상세 정보 (SQL, 근거 문서 등)
      - done   : 최종 답변
      - error  : 오류
    """

    async def event_stream() -> AsyncGenerator[str, None]:
        graph = get_graph()
        inputs = {"messages": to_langchain_messages(request.messages)}
        state: dict[str, Any] = {}

        try:
            yield sse("start", {"message": "워크플로를 시작합니다."})

            async for mode, chunk in graph.astream(
                inputs, stream_mode=["updates", "messages"]
            ):
                if mode == "messages":
                    message_chunk, metadata = chunk
                    if metadata.get("langgraph_node") not in ANSWER_NODES:
                        continue
                    # 이 스트림에는 LLM 토큰(AIMessageChunk)뿐 아니라, 노드가 상태에
                    # 기록한 완성된 AIMessage도 함께 실려 옵니다. 후자를 그대로 흘려보내면
                    # 답변 전문이 끝에 한 번 더 붙으므로 토큰 청크만 통과시킵니다.
                    if not isinstance(message_chunk, AIMessageChunk):
                        continue
                    text = getattr(message_chunk, "content", "")
                    if isinstance(text, str) and text:
                        yield sse("token", {"text": text})
                    continue

                # mode == "updates": 노드 하나가 끝날 때마다 상태 조각이 들어옴
                for node_name, update in chunk.items():
                    if not isinstance(update, dict):
                        continue

                    # 누적 상태 갱신 (messages는 최종 답변 추출용으로만 사용)
                    for key, value in update.items():
                        if key == "messages":
                            state.setdefault("messages", [])
                            state["messages"].extend(
                                value if isinstance(value, list) else [value]
                            )
                        else:
                            state[key] = value

                    yield sse(
                        "node",
                        {
                            "node": node_name,
                            "label": NODE_LABELS.get(node_name, node_name),
                        },
                    )

                    if node_name == "classify_intent" and update.get("intent"):
                        yield sse("intent", {"intent": update["intent"]})

            yield sse("meta", build_meta(state))
            yield sse("done", {"answer": extract_answer(state)})

        except asyncio.CancelledError:  # 클라이언트가 연결을 끊은 경우
            raise
        except Exception as exc:  # noqa: BLE001 - 오류를 UI로 그대로 전달
            yield sse("error", {"message": f"오류가 발생했습니다: {exc}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --------------------------------------------------------------------------
# 프로덕션: 빌드된 React 앱(web/dist)이 있으면 같은 서버에서 함께 제공
#   npm run build 이후 http://127.0.0.1:8000 하나로 접속 가능
# --------------------------------------------------------------------------

WEB_DIST = PROJECT_ROOT / "web" / "dist"

if WEB_DIST.is_dir():
    from fastapi.staticfiles import StaticFiles
    from starlette.exceptions import HTTPException as StarletteHTTPException

    class SPAStaticFiles(StaticFiles):
        """존재하지 않는 경로는 index.html로 폴백 (클라이언트 라우팅 지원)"""

        async def get_response(self, path: str, scope):
            try:
                return await super().get_response(path, scope)
            except StarletteHTTPException as exc:
                if exc.status_code != 404:
                    raise
                return await super().get_response("index.html", scope)

    app.mount("/", SPAStaticFiles(directory=WEB_DIST, html=True), name="web")
