import { useState } from 'react'
import {
  AlertTriangle,
  ChevronDown,
  Copy,
  Check,
  Database,
  FileSearch,
  Repeat2,
  Tag,
} from 'lucide-react'
import { displayPage, intentMeta, pdfPageUrl } from '../lib/intents.js'

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* 클립보드 권한이 없으면 조용히 무시 */
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-slate-400 transition hover:bg-slate-800 hover:text-slate-200"
    >
      {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
      {copied ? '복사됨' : '복사'}
    </button>
  )
}

function DocumentCard({ document, index }) {
  const [open, setOpen] = useState(false)
  const page = displayPage(document.page)
  const preview = document.content.replace(/\s+/g, ' ').slice(0, 90)

  return (
    <li className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-start gap-2 px-3 py-2.5 text-left transition hover:bg-slate-50"
      >
        <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded bg-brand-100 text-[10px] font-bold text-brand-700">
          {index + 1}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-1.5">
            {document.category && (
              <span className="inline-flex items-center gap-1 rounded bg-brand-50 px-1.5 py-0.5 text-[10px] font-medium text-brand-700">
                <Tag className="size-2.5" />
                {document.category}
              </span>
            )}
            {page !== null && (
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
                {page}쪽
              </span>
            )}
          </span>
          {!open && (
            <span className="mt-1 block truncate text-[12px] text-slate-500">{preview}…</span>
          )}
        </span>
        <ChevronDown
          className={`mt-0.5 size-4 shrink-0 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="border-t border-slate-100 bg-slate-50/60 px-3 py-3">
          <p className="text-[12px] leading-6 whitespace-pre-wrap text-slate-600">
            {document.content}
          </p>
          {page !== null && (
            <a
              href={pdfPageUrl(document.page)}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-block text-[11px] font-medium text-brand-600 underline underline-offset-2 hover:text-brand-700"
            >
              공고문 {page}쪽 원문 열기 →
            </a>
          )}
        </div>
      )}
    </li>
  )
}

export default function WorkflowPanel({ meta }) {
  const [open, setOpen] = useState(false)

  if (!meta) return null

  const info = intentMeta(meta.intent)
  const documents = meta.documents ?? []
  const hasDetails =
    documents.length > 0 || meta.sqlQuery || meta.rewrittenQuery || meta.error || meta.dbResults

  return (
    <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50/70">
      <div className="flex flex-wrap items-center gap-2 px-3 py-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-semibold ring-1 ring-inset ${info.badge}`}
        >
          <span className={`size-1.5 rounded-full ${info.dot}`} />
          {info.label}
        </span>

        {documents.length > 0 && (
          <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
            <FileSearch className="size-3.5" />
            근거 문서 {documents.length}건
          </span>
        )}

        {meta.sqlQuery && (
          <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
            <Database className="size-3.5" />
            SQL 실행
          </span>
        )}

        {meta.retryCount > 0 && (
          <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
            <Repeat2 className="size-3.5" />
            재시도 {meta.retryCount}회
          </span>
        )}

        {meta.error && (
          <span className="inline-flex items-center gap-1 text-[11px] text-amber-600">
            <AlertTriangle className="size-3.5" />
            조회 오류
          </span>
        )}

        {hasDetails && (
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="ml-auto inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-slate-500 transition hover:bg-slate-200/70 hover:text-slate-700"
          >
            {open ? '접기' : '자세히'}
            <ChevronDown className={`size-3.5 transition-transform ${open ? 'rotate-180' : ''}`} />
          </button>
        )}
      </div>

      {open && hasDetails && (
        <div className="space-y-4 border-t border-slate-200 px-3 py-3">
          <p className="text-[12px] text-slate-500">{info.hint}</p>

          {meta.rewrittenQuery && (
            <div>
              <h4 className="mb-1.5 text-[11px] font-semibold tracking-wide text-slate-400 uppercase">
                재작성된 검색 쿼리
              </h4>
              <p className="rounded-lg bg-white px-3 py-2 text-[12px] text-slate-600 ring-1 ring-slate-200">
                {meta.rewrittenQuery}
              </p>
            </div>
          )}

          {meta.sqlQuery && (
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <h4 className="text-[11px] font-semibold tracking-wide text-slate-400 uppercase">
                  실행된 SQL
                </h4>
              </div>
              <div className="overflow-hidden rounded-lg bg-slate-900">
                <div className="flex items-center justify-between border-b border-slate-800 px-3 py-1.5">
                  <span className="font-mono text-[10px] text-slate-500">PostgreSQL</span>
                  <CopyButton text={meta.sqlQuery} />
                </div>
                <pre className="scroll-thin overflow-x-auto px-3 py-2.5 font-mono text-[12px] leading-6 text-emerald-300">
                  {meta.sqlQuery}
                </pre>
              </div>
            </div>
          )}

          {meta.dbResults && (
            <div>
              <h4 className="mb-1.5 text-[11px] font-semibold tracking-wide text-slate-400 uppercase">
                조회 결과 (raw)
              </h4>
              <pre className="scroll-thin max-h-40 overflow-auto rounded-lg bg-white px-3 py-2 font-mono text-[11px] leading-5 whitespace-pre-wrap text-slate-600 ring-1 ring-slate-200">
                {meta.dbResults}
              </pre>
            </div>
          )}

          {documents.length > 0 && (
            <div>
              <h4 className="mb-1.5 text-[11px] font-semibold tracking-wide text-slate-400 uppercase">
                근거 문서
              </h4>
              <ul className="space-y-1.5">
                {documents.map((document, index) => (
                  <DocumentCard key={index} document={document} index={index} />
                ))}
              </ul>
            </div>
          )}

          {meta.error && (
            <div className="rounded-lg bg-amber-50 px-3 py-2 text-[12px] text-amber-800 ring-1 ring-amber-200">
              <span className="font-semibold">조회 중 오류가 있었습니다. </span>
              <span className="font-mono break-all">{meta.error}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
