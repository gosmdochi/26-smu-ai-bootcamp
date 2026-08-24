/** 질문 의도별 표시 정보 (LangGraph classify_intent 결과와 1:1 대응) */
export const INTENT_META = {
  vector: {
    label: '공고문 검색',
    hint: 'Qdrant 벡터 검색으로 모집공고문 본문에서 근거를 찾았습니다.',
    badge: 'bg-brand-50 text-brand-700 ring-brand-200',
    dot: 'bg-brand-500',
  },
  database: {
    label: '데이터 조회',
    hint: 'Text2SQL로 Supabase(PostgreSQL) 표 데이터를 조회했습니다.',
    badge: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    dot: 'bg-emerald-500',
  },
  general: {
    label: '일반 대화',
    hint: '검색 없이 모델이 직접 답변했습니다.',
    badge: 'bg-slate-100 text-slate-600 ring-slate-200',
    dot: 'bg-slate-400',
  },
}

export function intentMeta(intent) {
  return INTENT_META[intent] ?? INTENT_META.general
}

/** 공고문 PDF의 해당 페이지를 여는 링크 (메타데이터 page는 0부터 시작) */
export function pdfPageUrl(page) {
  const pageNumber = Number(page)
  if (!Number.isFinite(pageNumber)) return '/api/notice.pdf'
  return `/api/notice.pdf#page=${pageNumber + 1}`
}

/** 사람이 읽는 페이지 번호 */
export function displayPage(page) {
  const pageNumber = Number(page)
  return Number.isFinite(pageNumber) ? pageNumber + 1 : null
}
