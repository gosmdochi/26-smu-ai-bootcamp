import os
from langchain_community.utilities import SQLDatabase
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

# day3 노트북에서 CSV 3종을 Supabase(PostgreSQL)에 그대로 적재해 사용합니다.
# apartment / preferences / service_center / information 테이블이 이미 Supabase에 있어야 합니다.
DOMAIN_REASONING_HINT = """
<domain_reasoning_hints>
- 청년 1순위: 생계·의료·주거급여 수급, 보호대상 한부모, 차상위계층 (preferences 테이블)
- 청년 2순위: 본인+부모 소득 100% 이하 + 자산기준
- 청년 3순위: 1·2순위 미해당 + 본인 소득 100% 이하(1인가구)
- 청년 임대료구분(rent_grade): 1순위 → A(시중시세 30%), 2·3순위 → B(시중시세 50%)
- 신혼부부Ⅰ: 소득 50% → A, 70% → B, 90% → B
- 신혼부부Ⅱ: 소득 80% → C, 130% → D
- 금액 단위: deposit_total_k/contract_deposit_k/balance_k = 천원, monthly_rent = 원
- 소득기준 비교 시 preferences.criteria_value에서 숫자만 추출해 비교
- 복합 추론 질문은 preferences에서 기준을 먼저 조회한 뒤 apartment/service_center와 연결
- apartment/preferences/service_center는 "2026년 2차 서울시 청년안심주택" 이번 공고문 전용(특정 서울 단지) 데이터이고,
  information은 이와 별개로 전국 시/도·시/군/구 단위의 일반 청년주택 지역우선 조건·지자체 특화 주거지원·문의처를 다룸
- 질문에 서울 청년안심주택 특정 단지명(예: 에이트플레이스, 스타팰리스)이 없고, 다른 지역명(예: 화성시, 수원시, 강남구 등)이나
  "지역우선", "지자체 지원", "타 지역 청년주택" 등이 언급되면 information 테이블에서 조회
- information 조회 시 시/도·시/군/구 컬럼으로 필터링
</domain_reasoning_hints>
"""

TABLE_GUIDE = """
<table_guide>
- apartment (단지정보 · 이번 공고 전용): complex_name, address, supply_area_type, floor_plan_area,
  eligibility, units, rent_grade, deposit_total_k, contract_deposit_k, balance_k, monthly_rent
- preferences (자격요건 · 이번 공고 전용): eligibility, category_type, code, item, criteria_value, note
- service_center (문의처 · 이번 공고 전용): category, organization, service, phone, note
- information (전국 지자체별 청년주택 지원정보 · 이번 공고와 별개): 시/도·시/군/구별 청년 청약 당해(지역우선)
  거주조건 및 특징, 지자체 특화 주거지원(월세·보증금 대출이자·이사비 등), 세부 신청자격(연령·소득·무주택 기준),
  신청 및 문의 창구. 실제 컬럼명은 위 database_schema에 표시된 이름을 그대로 사용할 것(한글 컬럼명이면 큰따옴표로 감쌀 것)
</table_guide>
"""


class Text2SQLEngine:
    def __init__(self):
        """Text2SQL 엔진 초기화 (Supabase PostgreSQL 전용)"""
        supabase_db_url = os.getenv("SUPABASE_DB_URL")
        if not supabase_db_url:
            raise ValueError(
                "SUPABASE_DB_URL이 설정되어 있지 않습니다. "
                ".env에 apartment/preferences/service_center 테이블이 있는 "
                "Supabase PostgreSQL 연결 문자열을 설정하세요."
            )

        self.db = SQLDatabase.from_uri(supabase_db_url)
        self.llm = init_chat_model("gpt-5.4-mini")
        self.schema_info = self.db.get_table_info()

    def generate_sql(self, question: str, feedback: str = None) -> str:
        """
        자연어 질문을 SQL 쿼리로 변환

        Args:
            question: 사용자의 자연어 질문
            feedback: 이전 시도의 오류 피드백 (재시도 시)

        Returns:
            생성된 SQL 쿼리
        """
        system_prompt = f"""
당신은 2026년 2차 서울시 청년안심주택(공공임대) 청약 데이터 SQL 전문가입니다.
사용자의 질문을 정확한 PostgreSQL SELECT 쿼리로 변환하세요.

<database_schema>
{self.schema_info}
</database_schema>

{TABLE_GUIDE}
{DOMAIN_REASONING_HINT}

<rules>
- PostgreSQL 문법을 사용하세요
- SELECT 쿼리만 생성하세요 (INSERT, UPDATE, DELETE 금지)
- 결과는 최대 10개로 제한하세요 (LIMIT 10)
- SQL 쿼리만 반환하고, 설명은 포함하지 마세요
- 코드 블록(```)이나 'sql' 키워드 없이 순수 쿼리만 반환하세요
- NULL 값을 주의해서 처리하세요
- 존재하지 않는 컬럼을 사용하지 마세요
- JOIN이 필요한 경우 적절히 사용하세요
- 세미콜론(;)으로 쿼리를 종료하세요
</rules>
"""

        if feedback:
            system_prompt += f"\n\n이전 시도의 오류:\n{feedback}\n\n위 오류를 고려하여 쿼리를 수정하세요."

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question)
        ]

        response = self.llm.invoke(messages)
        sql_query = response.content.strip()

        # 코드 블록 제거
        if sql_query.startswith("```"):
            lines = sql_query.split("\n")
            sql_query = "\n".join(lines[1:-1]) if len(lines) > 2 else sql_query
            sql_query = sql_query.replace("sql", "", 1).strip() if sql_query.lower().startswith("sql") else sql_query

        return sql_query

    def execute_sql(self, sql_query: str) -> tuple[str, str]:
        """
        SQL 쿼리 실행

        Args:
            sql_query: 실행할 SQL 쿼리

        Returns:
            (결과 문자열, 오류 메시지) 튜플
        """
        try:
            result = self.db.run(sql_query)
            return result, None
        except Exception as e:
            error_msg = str(e)
            return None, error_msg

    def query(self, question: str, previous_error: str = None) -> dict:
        """
        질문에 대한 SQL 생성 및 실행

        Args:
            question: 사용자 질문
            previous_error: 이전 시도의 오류 (재시도 시)

        Returns:
            결과 딕셔너리 (sql_query, result, error)
        """
        sql_query = self.generate_sql(question, feedback=previous_error)
        result, error = self.execute_sql(sql_query)

        return {
            "sql_query": sql_query,
            "result": result,
            "error": error
        }

    def is_empty_result(self, result: str) -> bool:
        """
        결과가 비어있는지 확인

        Args:
            result: SQL 실행 결과

        Returns:
            결과가 비어있으면 True
        """
        if not result or not str(result).strip():
            return True

        empty_patterns = ["[]", "()", "[()]", "none", "no rows", "0 rows"]
        result_lower = str(result).lower().strip()

        return any(pattern == result_lower or pattern in result_lower for pattern in empty_patterns)


def get_text2sql_engine() -> Text2SQLEngine:
    """Text2SQL 엔진 인스턴스 반환"""
    return Text2SQLEngine()
