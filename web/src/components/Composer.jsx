import { useEffect, useRef } from 'react'
import { ArrowUp, Square } from 'lucide-react'

export default function Composer({ value, onChange, onSubmit, onStop, busy }) {
  const textareaRef = useRef(null)

  // 입력 높이 자동 조절 (최대 200px)
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
  }, [value])

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      if (!busy && value.trim()) onSubmit()
    }
  }

  return (
    <div className="border-t border-slate-200 bg-white/80 px-6 py-4 backdrop-blur">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-2xl border border-slate-300 bg-white p-2 shadow-sm transition focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-100">
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="청약 일정, 자격, 단지별 임대료 등 궁금한 점을 물어보세요"
            className="scroll-thin max-h-[200px] flex-1 resize-none bg-transparent px-2.5 py-2 text-[15px] leading-6 text-slate-800 placeholder:text-slate-400 focus:outline-none"
          />

          {busy ? (
            <button
              type="button"
              onClick={onStop}
              title="생성 중지"
              className="grid size-9 shrink-0 place-items-center rounded-xl bg-slate-800 text-white transition hover:bg-slate-700"
            >
              <Square className="size-3.5 fill-current" />
            </button>
          ) : (
            <button
              type="button"
              onClick={onSubmit}
              disabled={!value.trim()}
              title="보내기"
              className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand-600 text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
            >
              <ArrowUp className="size-4.5" />
            </button>
          )}
        </div>

        <p className="mt-2 text-center text-[11px] text-slate-400">
          공고문 기반으로 답변하지만 오류가 있을 수 있습니다. 최종 확인은 원본 공고문과 SH공사 안내를
          따르세요.
        </p>
      </div>
    </div>
  )
}
