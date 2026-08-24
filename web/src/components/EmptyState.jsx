import { CalendarDays, Coins, FileCheck2, House, Phone } from 'lucide-react'

const HIGHLIGHTS = [
  {
    icon: CalendarDays,
    title: '청약 일정',
    description: '접수 기간, 서류제출, 당첨자 발표 일정',
    question: '청약 접수는 언제부터 언제까지인가요?',
  },
  {
    icon: FileCheck2,
    title: '신청 자격 · 순위',
    description: '청년 / 신혼부부 계층별 소득·자산 기준',
    question: '청년 1순위 자격요건에 해당하는 경우는 어떤 경우들이 있나요?',
  },
  {
    icon: Coins,
    title: '단지별 임대조건',
    description: '평형별 보증금, 계약금, 잔금, 월 임대료',
    question: '에이트플레이스 39A 타입 임대보증금과 월세는 얼마인가요?',
  },
  {
    icon: Phone,
    title: '제출서류 · 문의처',
    description: '순위별 필수 서류와 유형별 상담 연락처',
    question: '청년 2순위로 신청하려면 어떤 서류가 필요한가요?',
  },
]

export default function EmptyState({ onPick }) {
  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center px-6 py-12 text-center">
      <div className="grid size-14 place-items-center rounded-2xl bg-brand-600 text-white shadow-lg shadow-brand-600/25">
        <House className="size-7" />
      </div>

      <h2 className="mt-5 text-2xl font-bold tracking-tight text-slate-900">
        68쪽 공고문, 질문 한 번으로 끝내세요
      </h2>
      <p className="mt-2 max-w-xl text-[15px] leading-7 text-slate-500">
        2026년 2차 서울시 청년안심주택(공공임대) 모집공고문과 단지·자격 데이터를 학습한 도우미입니다.
        일정·자격·임대조건·서류를 근거와 함께 알려드립니다.
      </p>

      <div className="mt-9 grid w-full gap-3 sm:grid-cols-2">
        {HIGHLIGHTS.map(({ icon: Icon, title, description, question }) => (
          <button
            key={title}
            type="button"
            onClick={() => onPick(question)}
            className="group flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 text-left transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-md"
          >
            <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-brand-50 text-brand-600 transition group-hover:bg-brand-100">
              <Icon className="size-4.5" />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-slate-800">{title}</span>
              <span className="mt-0.5 block text-[13px] leading-snug text-slate-500">
                {description}
              </span>
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
