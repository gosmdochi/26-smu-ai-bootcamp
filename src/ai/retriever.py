import os
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

# day2 노트북에서 적재한 실제 컬렉션 (단일 컬렉션 + category 메타데이터)
COLLECTION_NAME = "cheongnyeon_anshim_housing"

# 공고문 목차(1~14장) 기준 12개 카테고리 (README / day2 노트북 기준)
VALID_CATEGORIES = [
    "공급일정",
    "공급현황",
    "임대조건",
    "신청자격",
    "신청접수",
    "제출서류",
    "당첨자발표",
    "계약입주",
    "거주기간",
    "신청유의사항",
    "단지유의사항",
    "추가안내",
]


class VectorRetriever:
    """2026년 2차 서울시 청년안심주택 모집공고문 Qdrant 검색기"""

    def __init__(self):
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )

        # day2 노트북 적재 시 사용한 임베딩 모델과 반드시 동일해야 함
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        self.vectorstore = QdrantVectorStore(
            client=self.client,
            collection_name=COLLECTION_NAME,
            embedding=self.embeddings,
        )

    def _build_filter(self, categories: Optional[List[str]]) -> Optional[models.Filter]:
        """카테고리 리스트를 Qdrant 필터로 변환 (여러 개는 OR)"""
        if not categories:
            return None

        conditions = [
            models.FieldCondition(
                key="metadata.category",
                match=models.MatchValue(value=cat),
            )
            for cat in categories
            if cat in VALID_CATEGORIES
        ]

        if not conditions:
            return None

        if len(conditions) == 1:
            return models.Filter(must=conditions)
        return models.Filter(should=conditions)

    def search(
        self,
        query: str,
        k: int = 3,
        score_threshold: float = 0.5,
        categories: Optional[List[str]] = None,
    ) -> List[Document]:
        """
        카테고리 필터를 적용한 벡터 검색

        Args:
            query: 검색 쿼리
            k: 반환할 문서 개수
            score_threshold: 최소 유사도 임계값 (현재 similarity_search에는 미적용, 호환성 유지)
            categories: 카테고리 필터 리스트 (선택사항, None이면 전체 문서 대상 검색)

        Returns:
            검색된 문서 리스트
        """
        try:
            filter_conditions = self._build_filter(categories)
            results = self.vectorstore.similarity_search(
                query,
                k=k,
                filter=filter_conditions,
            )
            return results
        except Exception as e:
            print(f"벡터 검색 오류: {e}")
            # 필터 관련 오류(예: 인덱스 미생성)일 경우 필터 없이 재시도
            try:
                return self.vectorstore.similarity_search(query, k=k)
            except Exception as e2:
                print(f"벡터 검색 재시도 오류: {e2}")
                return []

    def is_relevant(self, results: List[Document], min_count: int = 1) -> bool:
        """검색 결과가 충분한지 확인"""
        return len(results) >= min_count


def get_retriever() -> VectorRetriever:
    """벡터 검색기 인스턴스 반환"""
    return VectorRetriever()
