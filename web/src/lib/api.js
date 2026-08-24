/**
 * FastAPI 백엔드(src/api/main.py)와 통신하는 클라이언트.
 * 개발 중에는 vite.config.js의 프록시가 /api 요청을 8000 포트로 넘겨줍니다.
 */

export async function fetchHealth() {
  const response = await fetch('/api/health')
  if (!response.ok) throw new Error('서버 상태를 확인할 수 없습니다.')
  return response.json()
}

export async function fetchExamples() {
  const response = await fetch('/api/examples')
  if (!response.ok) throw new Error('예시 질문을 불러올 수 없습니다.')
  return response.json()
}

/**
 * SSE 프레임 하나를 { event, data }로 파싱합니다.
 */
function parseFrame(frame) {
  let event = 'message'
  const dataLines = []

  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart())
    }
  }

  if (dataLines.length === 0) return null

  try {
    return { event, data: JSON.parse(dataLines.join('\n')) }
  } catch {
    return { event, data: { raw: dataLines.join('\n') } }
  }
}

/**
 * 채팅 스트리밍 요청.
 *
 * @param {object}   options
 * @param {Array}    options.messages  [{ role, content }] 형태의 대화 히스토리
 * @param {AbortSignal} options.signal 중단 시그널
 * @param {object}   options.handlers  { onStart, onNode, onIntent, onToken, onMeta, onDone, onError }
 */
export async function streamChat({ messages, signal, handlers = {} }) {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new Error(`서버 응답 오류 (${response.status})`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const dispatch = {
    start: handlers.onStart,
    node: handlers.onNode,
    intent: handlers.onIntent,
    token: handlers.onToken,
    meta: handlers.onMeta,
    done: handlers.onDone,
    error: handlers.onError,
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // 프레임 구분자는 빈 줄(\n\n). CRLF 환경도 함께 처리합니다.
    const frames = buffer.split(/\r?\n\r?\n/)
    buffer = frames.pop() ?? ''

    for (const frame of frames) {
      if (!frame.trim()) continue
      const parsed = parseFrame(frame)
      if (!parsed) continue
      dispatch[parsed.event]?.(parsed.data)
    }
  }
}
