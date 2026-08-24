from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from ai.state import AgentState
from ai.retriever import get_retriever
from ai.text2sql import get_text2sql_engine
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, List

load_dotenv()

llm = init_chat_model("gpt-5.4-mini")

_retriever = None
_text2sql_engine = None


class VectorSearchQuery(BaseModel):
    """벡터 검색을 위한 쿼리 분석 결과"""
    optimized_query: str = Field(
        description="검색에 최적화된 쿼리. 핵심 키워드를 포함하고 명확하게 작성."
    )
    categories: Optional[List[str]] = Field(
        default=None,
        description="선택된 카테고리 리스트 (1-2개). 명확하게 관련 있는 카테고리만 선택. 애매하거나 불확실한 경우 null 반환. 가능한 값: 공급일정, 공급현황, 임대조건, 신청자격, 신청접수, 제출서류, 당첨자발표, 계약입주, 거주기간, 신청유의사항, 단지유의사항, 추가안내"
    )


def get_cached_retriever():
    """캐시된 retriever 인스턴스 반환 (lazy initialization)"""
    global _retriever
    if _retriever is None:
        _retriever = get_retriever()
    return _retriever


def get_cached_text2sql_engine():
    """캐시된 text2sql_engine 인스턴스 반환 (lazy initialization)"""
    global _text2sql_engine
    if _text2sql_engine is None:
        _text2sql_engine = get_text2sql_engine()
    return _text2sql_engine


def classify_intent(state: AgentState) -> AgentState:
    """
    사용자 질문의 의도를 분류하는 노드

    분류 결과:
    - 'general': 일반적인 대화나 인사
    - 'database': 데이터베이스 조회가 필요한 질문
    - 'vector': 문서 검색이 필요한 질문

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태
    """
    # messages에서 질문 추출
    messages = state.get("messages", [])
    if not messages:
        raise ValueError("No messages provided")

    # 마지막 사용자 메시지를 질문으로 사용
    question = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])

    system_prompt = """
당신은 사용자 질문의 의도를 분류하는 전문가입니다.

이전 대화 맥락을 고려하여 현재 질문을 다음 3가지 중 하나로 분류하세요:

1. 'general' - 일반적인 대화, 인사, 간단한 질문
   예: "안녕하세요", "고마워", "날씨 어때?"

2. 'database' - 단지별 임대조건, 자격요건 표, 상담센터 연락처, 타 지자체 청년주택 지원제도 등 정형 데이터(표) 조회가 필요한 질문
   예: "에이트플레이스 39A 타입 임대보증금은?", "청년 1순위 자격요건에 해당하는 경우는?", "민간임대 계약 문의처는?",
       "화성시 청년 전월세 보증금 대출이자 지원은 얼마인가요?", "강남구 청년주택 지역우선 조건이 뭔가요?"

3. 'vector' - 청약 일정, 제출서류, 신청 절차, 유의사항 등 모집공고문 본문 검색이 필요한 질문
   예: "청약 접수는 언제부터 언제까지인가요?", "청년 2순위 제출서류는?", "반려동물 키울 수 있나요?"

반드시 'general', 'database', 'vector' 중 하나만 답변하세요.
다른 설명 없이 분류 결과만 반환하세요.
"""

    # 시스템 메시지 + 전체 대화 히스토리
    conversation = [SystemMessage(content=system_prompt)] + messages

    response = llm.invoke(conversation)
    intent = response.content.strip().lower()

    # 유효한 의도인지 확인
    if intent not in ['general', 'database', 'vector']:
        intent = 'general'

    return {
        "intent": intent,
        "question": question
    }


def general_answer(state: AgentState) -> AgentState:
    """
    일반적인 질문에 직접 답변하는 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태
    """
    # 대화 히스토리 가져오기
    messages = state.get("messages", [])

    system_prompt = """
당신은 친절한 AI 어시스턴트입니다.
사용자의 질문에 자연스럽고 도움이 되는 답변을 제공하세요.
"""

    # 시스템 메시지 + 기존 대화 히스토리
    conversation = [SystemMessage(content=system_prompt)] + messages

    response = llm.invoke(conversation)
    answer = response.content

    return {
        "messages": [AIMessage(content=answer)]
    }


def vector_search(state: AgentState) -> AgentState:
    """
    Qdrant 벡터 검색을 수행하는 노드

    1. LLM으로 질문 분석 (최적화된 쿼리 + 카테고리 추출)
    2. 병렬 벡터 검색 수행

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태
    """
    # 대화 히스토리 가져오기
    messages = state.get("messages", [])

    # 재작성된 쿼리가 있으면 사용, 없으면 원본 질문 사용
    original_query = state.get("rewritten_query") or state.get("question", "")

    # 이전 대화 맥락이 있으면 완전한 질문으로 재구성
    if len(messages) > 1 and not state.get("rewritten_query"):
        # rewritten_query가 없을 때만 (첫 시도) 맥락 고려
        system_prompt_complete = """
당신은 질문 분석 전문가입니다.
이전 대화 맥락을 고려하여 현재 질문을 완전하고 명확한 질문으로 재구성하세요.

예시:
- 이전: "청약 접수는 언제부터?" → 현재: "서류는 뭐가 필요해?" → 재구성: "청약 접수 시 필요한 서류는 뭐가 필요해?"
- 이전: "청년안심주택 제출서류" → 현재: "더 자세히 알려줘" → 재구성: "청년안심주택 제출서류를 더 자세히 알려줘"

완전한 질문만 반환하세요. 설명은 포함하지 마세요.
만약 현재 질문이 이미 완전하다면 그대로 반환하세요.
"""
        conversation_complete = [SystemMessage(content=system_prompt_complete)] + messages
        response_complete = llm.invoke(conversation_complete)
        original_query = response_complete.content.strip()

    # 1. LLM으로 쿼리 분석 및 카테고리 추출 (Structured Output)
    # 시스템 프롬프트: 역할 정의 및 카테고리 설명
    system_prompt = """당신은 검색 쿼리 최적화 전문가입니다.
사용자의 질문을 분석하여 벡터 검색에 최적화된 쿼리를 생성하고, 적절한 카테고리를 선택하는 역할을 수행합니다.

사용 가능한 카테고리:
- 공급일정: 접수 일정, 공고 시점 등 일정 관련
- 공급현황: 단지별 시공사, 세대수 등 공급 현황
- 임대조건: 보증금, 계약금, 잔금, 월임대료 등 임대 조건
- 신청자격: 나이·소득·자산 기준, 순위, 무주택 요건 등 자격 관련
- 신청접수: 접수 방법, 접수처 관련
- 제출서류: 순위별 필수 제출 서류 목록
- 당첨자발표: 당첨자 발표 일정 및 방법
- 계약입주: 계약, 입주 절차 관련
- 거주기간: 거주기간, 재계약, 갱신 규정
- 신청유의사항: 신청 시 주의사항
- 단지유의사항: 반려동물, 주차 등 입주 후 생활 유의사항
- 추가안내: 소득·자산·금융 등 기타 안내 사항

카테고리 선택 규칙:
1. 명확하게 관련 있는 카테고리를 1-2개 선택합니다
2. 여러 카테고리와 관련될 수 있으면 최대 2개까지 선택
3. 애매하거나 확신이 없으면 반드시 null을 반환 (잘못된 카테고리보다 null이 나음)
4. 억지로 카테고리를 선택하지 말고, 확실한 경우에만 선택

출력 지침:
1. optimized_query: 검색에 효과적인 핵심 키워드를 포함한 쿼리로 최적화
2. categories: 명확하게 관련 있는 카테고리 1-2개를 리스트로 반환. 불확실하면 null"""

    # 유저 프롬프트: 실제 질문
    user_prompt = f"다음 질문을 분석해주세요:\n\n{original_query}"

    # 메시지 객체 생성 (Structured Output용)
    llm_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    # Structured Output으로 LLM 호출
    structured_llm = llm.with_structured_output(VectorSearchQuery)
    query_analysis = structured_llm.invoke(llm_messages)

    optimized_query = query_analysis.optimized_query
    categories = query_analysis.categories

    print(f"[벡터 검색 쿼리 분석]")
    print(f"  원본 쿼리: {original_query}")
    print(f"  최적화된 쿼리: {optimized_query}")
    print(f"  선택된 카테고리: {categories}")

    # 2. 병렬 벡터 검색 수행 (카테고리 필터 적용)
    retriever = get_cached_retriever()
    results = retriever.search(optimized_query, k=3, score_threshold=0.5, categories=categories)

    return {
        "vector_results": results
    }


def rewrite_query(state: AgentState) -> AgentState:
    """
    검색 결과가 부족할 때 쿼리를 재작성하는 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태
    """
    # 대화 히스토리 가져오기
    messages = state.get("messages", [])

    system_prompt = """
당신은 검색 쿼리 최적화 전문가입니다.

사용자의 질문이 검색 결과를 얻지 못했습니다.
이전 대화 맥락을 고려하여 질문을 다시 작성하여 더 나은 검색 결과를 얻을 수 있도록 하세요.

최적화 방법:
- 이전 대화에서 언급된 맥락을 포함
- 동의어나 관련 용어 추가
- 질문을 더 구체적이거나 더 일반적으로 변경
- 핵심 키워드 강조

재작성된 쿼리만 반환하세요. 설명은 포함하지 마세요.
"""

    # 시스템 메시지 + 전체 대화 히스토리
    conversation = [SystemMessage(content=system_prompt)] + messages

    response = llm.invoke(conversation)
    rewritten = response.content.strip()

    return {
        "rewritten_query": rewritten,
        "retry_count": state.get("retry_count", 0) + 1
    }


def database_query(state: AgentState) -> AgentState:
    """
    Text2SQL을 수행하여 데이터베이스를 조회하는 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태
    """
    # 대화 히스토리 가져오기
    messages = state.get("messages", [])
    question = state.get("question", "")
    previous_error = state.get("error")

    # 이전 대화 맥락이 있으면 완전한 질문으로 재구성
    if len(messages) > 1:
        system_prompt = """
당신은 질문 분석 전문가입니다.
이전 대화 맥락을 고려하여 현재 질문을 완전하고 명확한 질문으로 재구성하세요.

예시:
- 이전: "에이트플레이스 39A 타입 알려줘" → 현재: "보증금은?" → 재구성: "에이트플레이스 39A 타입 보증금은?"
- 이전: "청년 1순위" → 현재: "자격요건이 뭐야?" → 재구성: "청년 1순위 자격요건이 뭐야?"

완전한 질문만 반환하세요. 설명은 포함하지 마세요.
만약 현재 질문이 이미 완전하다면 그대로 반환하세요.
"""
        conversation = [SystemMessage(content=system_prompt)] + messages
        response = llm.invoke(conversation)
        complete_question = response.content.strip()
    else:
        complete_question = question

    # Text2SQL 실행
    text2sql_engine = get_cached_text2sql_engine()
    result = text2sql_engine.query(complete_question, previous_error=previous_error)

    return {
        "sql_query": result["sql_query"],
        "db_results": result["result"],
        "error": result["error"],
        "retry_count": state.get("retry_count", 0) + 1
    }


def generate_answer(state: AgentState) -> AgentState:
    """
    검색 결과를 바탕으로 최종 답변을 생성하는 노드

    Args:
        state: 현재 상태

    Returns:
        업데이트된 상태
    """
    # 대화 히스토리 가져오기
    messages = state.get("messages", [])

    # 컨텍스트 구성
    context_parts = []

    # 벡터 검색 결과가 있으면 추가
    if state.get("vector_results"):
        docs = state["vector_results"]
        context_parts.append("관련 문서:")
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "알 수 없음")
            page = doc.metadata.get("page", "?")
            category = doc.metadata.get("category", "")

            # 출처 정보 구성
            source_info = f"출처: {source}, 페이지: {page}"
            if category:
                source_info += f", 카테고리: {category}"

            context_parts.append(f"\n[문서 {i}] {source_info}\n{doc.page_content}")

    # DB 검색 결과가 있으면 추가
    if state.get("db_results"):
        context_parts.append(f"\n\n데이터베이스 조회 결과:\n{state['db_results']}")
        if state.get("sql_query"):
            context_parts.append(f"\n실행된 SQL:\n{state['sql_query']}")

    context = "\n".join(context_parts)

    system_prompt = f"""
당신은 2026년 2차 서울시 청년안심주택(공공임대) 청약 안내 전문가입니다.

다음 정보를 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공하세요:

<context>
{context}
</context>

답변 시 다음 규칙을 따르세요:
- 주어진 정보를 자연스럽고 간결하게 전달하세요
- 구체적인 일정, 금액(원/천원 단위 구분), 순위, 서류명, 연락처 등의 정보를 명확히 포함하세요
- 불필요한 전제 조건이나 한계를 언급하지 말고, 질문에 직접 답변하세요
- 정보가 정말로 없는 경우에만 "해당 정보를 찾을 수 없습니다"라고 말하세요
- 청약을 준비하는 신청자에게 도움이 되는 친절하고 자연스러운 어조로 답변하세요
- 이전 대화 맥락을 고려하여 답변하세요
"""

    # 시스템 메시지 + 기존 대화 히스토리
    conversation = [SystemMessage(content=system_prompt)] + messages

    response = llm.invoke(conversation)
    answer = response.content

    return {
        "messages": [AIMessage(content=answer)]
    }


def route_by_intent(state: AgentState) -> str:
    """
    의도에 따라 다음 노드를 결정하는 라우팅 함수

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    intent = state.get("intent", "general")

    if intent == "general":
        return "general_answer"
    elif intent == "database":
        return "database_query"
    elif intent == "vector":
        return "vector_search"
    else:
        return "general_answer"


def check_vector_results(state: AgentState) -> str:
    """
    벡터 검색 결과를 확인하고 다음 노드를 결정하는 함수

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    results = state.get("vector_results", [])
    retry_count = state.get("retry_count", 0)

    # 결과가 있거나 재시도 횟수가 2회 이상이면 답변 생성
    retriever = get_cached_retriever()
    if retriever.is_relevant(results) or retry_count >= 2:
        return "generate_answer"
    else:
        return "rewrite_query"


def check_db_results(state: AgentState) -> str:
    """
    데이터베이스 검색 결과를 확인하고 다음 노드를 결정하는 함수

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    error = state.get("error")
    result = state.get("db_results")
    retry_count = state.get("retry_count", 0)

    # 오류가 없고 결과가 있으면 답변 생성
    text2sql_engine = get_cached_text2sql_engine()
    if not error and result and not text2sql_engine.is_empty_result(result):
        return "generate_answer"

    # 재시도 횟수가 2회 이상이면 답변 생성 (오류 메시지 포함)
    if retry_count >= 2:
        return "generate_answer"

    # 재시도
    return "database_query"
