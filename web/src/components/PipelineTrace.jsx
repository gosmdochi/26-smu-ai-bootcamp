import { Check, ChevronRight, Loader2 } from 'lucide-react'

/**
 * LangGraph 워크플로가 거쳐 간 노드를 순서대로 보여줍니다.
 * 노드는 실행이 끝난 시점에 서버에서 전송되므로, 진행 중일 때는 마지막에 로딩 칩을 붙입니다.
 */
export default function PipelineTrace({ steps, active }) {
  if (steps.length === 0 && !active) return null

  return (
    <div className="flex flex-wrap items-center gap-x-1 gap-y-1.5">
      {steps.map((step, index) => (
        <div key={`${step.node}-${index}`} className="flex items-center gap-1">
          {index > 0 && <ChevronRight className="size-3 text-slate-300" />}
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-600">
            <Check className="size-3 text-emerald-500" />
            {step.label}
          </span>
        </div>
      ))}

      {active && (
        <div className="flex items-center gap-1">
          {steps.length > 0 && <ChevronRight className="size-3 text-slate-300" />}
          <span className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-2 py-1 text-[11px] font-medium text-brand-700">
            <Loader2 className="size-3 animate-spin" />
            처리 중
          </span>
        </div>
      )}
    </div>
  )
}
