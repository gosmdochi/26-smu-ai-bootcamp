import {
  CheckCircle2,
  ExternalLink,
  FileText,
  House,
  Loader2,
  RotateCcw,
  Sparkles,
  XCircle,
} from 'lucide-react'
import { intentMeta } from '../lib/intents.js'

function EnvStatus({ health, loading }) {
  if (loading) {
    return (
      <p className="flex items-center gap-2 px-1 text-sm text-slate-500">
        <Loader2 className="size-4 animate-spin" />
        연결 상태 확인 중…
      </p>
    )
  }

  if (!health) {
    return (
      <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700 ring-1 ring-rose-200">
        API 서버에 연결할 수 없습니다.
        <span className="mt-1 block font-mono text-[11px] text-rose-600">
          uvicorn api.main:app --reload
        </span>
      </p>
    )
  }

  return (
    <ul className="space-y-1.5">
      {health.env.map((item) => (
        <li key={item.key} className="flex items-center gap-2 text-sm">
          {item.configured ? (
            <CheckCircle2 className="size-4 shrink-0 text-emerald-500" />
          ) : (
            <XCircle className="size-4 shrink-0 text-rose-500" />
          )}
          <span className={item.configured ? 'text-slate-600' : 'text-rose-600'}>
            {item.label}
          </span>
        </li>
      ))}
    </ul>
  )
}

export default function Sidebar({ health, healthLoading, exampleGroups, onExampleClick, onReset, busy }) {
  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-r border-slate-200 bg-white">
      <div className="flex items-start gap-3 border-b border-slate-200 px-5 py-5">
        <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand-600 text-white shadow-sm shadow-brand-600/30">
          <House className="size-5" />
        </div>
        <div className="min-w-0">
          <h1 className="text-[15px] leading-tight font-bold text-slate-900">
            청년안심주택 청약 도우미
          </h1>
          <p className="mt-0.5 text-xs text-slate-500">2026년 2차 서울시 공공임대</p>
        </div>
      </div>

      <div className="scroll-thin flex-1 space-y-6 overflow-y-auto px-5 py-5">
        <section>
          <h2 className="mb-2.5 text-xs font-semibold tracking-wide text-slate-400 uppercase">
            연결 상태
          </h2>
          <EnvStatus health={health} loading={healthLoading} />
        </section>

        <section>
          <h2 className="mb-2.5 flex items-center gap-1.5 text-xs font-semibold tracking-wide text-slate-400 uppercase">
            <Sparkles className="size-3.5" />
            예시 질문
          </h2>
          <div className="space-y-4">
            {exampleGroups.map((group) => {
              const meta = intentMeta(group.intent)
              return (
                <div key={group.intent}>
                  <div className="mb-1.5 flex items-center gap-1.5">
                    <span className={`size-1.5 rounded-full ${meta.dot}`} />
                    <span className="text-[11px] font-medium text-slate-500">{group.label}</span>
                  </div>
                  <ul className="space-y-1.5">
                    {group.items.map((question) => (
                      <li key={question}>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => onExampleClick(question)}
                          className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-[13px] leading-snug text-slate-600 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-800 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {question}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}
          </div>
        </section>
      </div>

      <div className="space-y-2 border-t border-slate-200 px-5 py-4">
        <a
          href="/api/notice.pdf"
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
        >
          <span className="flex items-center gap-2">
            <FileText className="size-4 text-slate-400" />
            모집공고문 원본 (68p)
          </span>
          <ExternalLink className="size-3.5 text-slate-400" />
        </a>
        <button
          type="button"
          onClick={onReset}
          disabled={busy}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-[13px] text-slate-500 transition hover:bg-slate-100 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RotateCcw className="size-4" />
          대화 초기화
        </button>
      </div>
    </aside>
  )
}
