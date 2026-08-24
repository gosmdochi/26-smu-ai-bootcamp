import { useCallback, useEffect, useRef, useState } from 'react'
import { Menu, MessageSquarePlus, X } from 'lucide-react'
import Sidebar from './components/Sidebar.jsx'
import MessageBubble from './components/MessageBubble.jsx'
import Composer from './components/Composer.jsx'
import EmptyState from './components/EmptyState.jsx'
import { fetchExamples, fetchHealth, streamChat } from './lib/api.js'

// 서버에서 예시 질문을 못 받아왔을 때 쓰는 기본값
const FALLBACK_EXAMPLES = [
  {
    intent: 'vector',
    label: '공고문 검색',
    items: ['청약 접수는 언제부터 언제까지인가요?', '반려동물을 키울 수 있나요?'],
  },
  {
    intent: 'database',
    label: '데이터 조회',
    items: ['에이트플레이스 39A 타입 임대보증금과 월세는 얼마인가요?'],
  },
]

let messageSeq = 0
const nextId = () => `m${++messageSeq}`

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [health, setHealth] = useState(null)
  const [healthLoading, setHealthLoading] = useState(true)
  const [exampleGroups, setExampleGroups] = useState(FALLBACK_EXAMPLES)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const abortRef = useRef(null)
  const scrollRef = useRef(null)
  const stickToBottomRef = useRef(true)

  // 초기 데이터 로드
  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setHealthLoading(false))

    fetchExamples()
      .then((data) => {
        if (data?.groups?.length) setExampleGroups(data.groups)
      })
      .catch(() => {})
  }, [])

  // 사용자가 위로 스크롤했으면 자동 스크롤을 멈춤
  const handleScroll = () => {
    const element = scrollRef.current
    if (!element) return
    const distance = element.scrollHeight - element.scrollTop - element.clientHeight
    stickToBottomRef.current = distance < 120
  }

  useEffect(() => {
    if (!stickToBottomRef.current) return
    const element = scrollRef.current
    if (element) element.scrollTop = element.scrollHeight
  }, [messages])

  const patchAssistant = useCallback((id, patch) => {
    setMessages((previous) =>
      previous.map((message) =>
        message.id === id
          ? { ...message, ...(typeof patch === 'function' ? patch(message) : patch) }
          : message,
      ),
    )
  }, [])

  const send = useCallback(
    async (rawText) => {
      const text = rawText.trim()
      if (!text || busy) return

      // 서버로 보낼 대화 히스토리 (실패한 답변은 제외)
      const history = messages
        .filter((message) => message.role === 'user' || (message.status === 'done' && message.content))
        .map(({ role, content }) => ({ role, content }))
      const payload = [...history, { role: 'user', content: text }]

      const assistantId = nextId()
      setMessages((previous) => [
        ...previous,
        { id: nextId(), role: 'user', content: text },
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          steps: [],
          meta: null,
          status: 'streaming',
          error: null,
        },
      ])
      setInput('')
      setBusy(true)
      stickToBottomRef.current = true

      const controller = new AbortController()
      abortRef.current = controller

      try {
        await streamChat({
          messages: payload,
          signal: controller.signal,
          handlers: {
            onNode: (data) =>
              patchAssistant(assistantId, (message) => ({
                steps: [...message.steps, { node: data.node, label: data.label }],
              })),
            onToken: (data) =>
              patchAssistant(assistantId, (message) => ({
                content: message.content + data.text,
              })),
            onMeta: (data) => patchAssistant(assistantId, { meta: data }),
            onDone: (data) =>
              patchAssistant(assistantId, (message) => ({
                // 토큰 스트리밍을 지원하지 않는 모델이면 여기서 전체 답변이 들어옵니다.
                content: data.answer || message.content,
                status: 'done',
              })),
            onError: (data) =>
              patchAssistant(assistantId, { status: 'error', error: data.message }),
          },
        })

        // done 이벤트 없이 스트림이 끝난 경우 대비
        patchAssistant(assistantId, (message) =>
          message.status === 'streaming' ? { status: 'done' } : {},
        )
      } catch (error) {
        if (error.name === 'AbortError') {
          patchAssistant(assistantId, (message) => ({
            status: message.content ? 'done' : 'error',
            error: message.content ? null : '생성을 중지했습니다.',
          }))
        } else {
          patchAssistant(assistantId, {
            status: 'error',
            error: `${error.message} — API 서버(uvicorn)가 실행 중인지 확인해 주세요.`,
          })
        }
      } finally {
        abortRef.current = null
        setBusy(false)
      }
    },
    [busy, messages, patchAssistant],
  )

  const stop = () => abortRef.current?.abort()

  const reset = () => {
    abortRef.current?.abort()
    setMessages([])
    setInput('')
    setDrawerOpen(false)
  }

  const pickExample = (question) => {
    setDrawerOpen(false)
    send(question)
  }

  const sidebar = (
    <Sidebar
      health={health}
      healthLoading={healthLoading}
      exampleGroups={exampleGroups}
      onExampleClick={pickExample}
      onReset={reset}
      busy={busy}
    />
  )

  return (
    <div className="flex h-full">
      <div className="hidden h-full lg:block">{sidebar}</div>

      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-slate-900/40"
            onClick={() => setDrawerOpen(false)}
            aria-hidden
          />
          <div className="absolute top-0 left-0 h-full shadow-2xl">
            {sidebar}
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              className="absolute top-4 -right-11 grid size-9 place-items-center rounded-lg bg-white text-slate-600 shadow"
            >
              <X className="size-4" />
            </button>
          </div>
        </div>
      )}

      <main className="flex min-w-0 flex-1 flex-col bg-slate-50">
        <header className="flex items-center gap-3 border-b border-slate-200 bg-white/80 px-5 py-3 backdrop-blur">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            className="grid size-9 place-items-center rounded-lg text-slate-500 transition hover:bg-slate-100 lg:hidden"
          >
            <Menu className="size-5" />
          </button>

          <div className="min-w-0 flex-1">
            <h2 className="truncate text-sm font-semibold text-slate-800">
              2026년 2차 서울시 청년안심주택 청약 상담
            </h2>
            <p className="truncate text-[11px] text-slate-400">
              RAG(Qdrant) + Text2SQL(Supabase) · LangGraph 워크플로
            </p>
          </div>

          {messages.length > 0 && (
            <button
              type="button"
              onClick={reset}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-[13px] text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
            >
              <MessageSquarePlus className="size-4" />
              새 대화
            </button>
          )}
        </header>

        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="scroll-thin flex-1 overflow-y-auto"
        >
          {messages.length === 0 ? (
            <EmptyState onPick={pickExample} />
          ) : (
            <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
            </div>
          )}
        </div>

        <Composer
          value={input}
          onChange={setInput}
          onSubmit={() => send(input)}
          onStop={stop}
          busy={busy}
        />
      </main>
    </div>
  )
}
