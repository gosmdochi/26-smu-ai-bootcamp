import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { AlertCircle, House, User } from 'lucide-react'
import PipelineTrace from './PipelineTrace.jsx'
import WorkflowPanel from './WorkflowPanel.jsx'

function UserMessage({ content }) {
  return (
    <div className="flex justify-end gap-3">
      <div className="max-w-[78%] rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 text-[15px] leading-7 whitespace-pre-wrap text-white shadow-sm">
        {content}
      </div>
      <div className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-full bg-slate-200 text-slate-500">
        <User className="size-4" />
      </div>
    </div>
  )
}

function AssistantMessage({ message }) {
  const streaming = message.status === 'streaming'
  const failed = message.status === 'error'

  return (
    <div className="flex gap-3">
      <div className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-full bg-brand-600 text-white shadow-sm shadow-brand-600/25">
        <House className="size-4" />
      </div>

      <div className="min-w-0 max-w-[85%] flex-1">
        {streaming && (
          <div className="mb-2">
            <PipelineTrace steps={message.steps} active />
          </div>
        )}

        {failed ? (
          <div className="flex items-start gap-2 rounded-2xl rounded-tl-sm border border-rose-200 bg-rose-50 px-4 py-3 text-[14px] text-rose-800">
            <AlertCircle className="mt-0.5 size-4 shrink-0" />
            <span>{message.error || '답변 생성 중 오류가 발생했습니다.'}</span>
          </div>
        ) : (
          <div className="rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3 shadow-sm">
            {message.content ? (
              <div className="md">
                <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown>
                {streaming && <span className="caret" />}
              </div>
            ) : (
              <p className="flex items-center gap-1.5 py-1 text-[14px] text-slate-400">
                답변을 준비하고 있습니다
                <span className="flex gap-1">
                  <span className="size-1 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
                  <span className="size-1 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
                  <span className="size-1 animate-bounce rounded-full bg-slate-400" />
                </span>
              </p>
            )}
          </div>
        )}

        {!streaming && <WorkflowPanel meta={message.meta} />}
      </div>
    </div>
  )
}

export default function MessageBubble({ message }) {
  return message.role === 'user' ? (
    <UserMessage content={message.content} />
  ) : (
    <AssistantMessage message={message} />
  )
}
