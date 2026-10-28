import { useEffect, useState, useRef, useCallback } from 'react'
import { AgentEvent } from '../api/endpoints'

interface UseSSEOptions {
  onEvent?: (event: AgentEvent) => void
  onError?: (err: any) => void
  onComplete?: () => void
}

export function useSSE(sessionId: string | null, options: UseSSEOptions = {}) {
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const optionsRef = useRef(options)

  useEffect(() => {
    optionsRef.current = options
  }, [options])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  useEffect(() => {
    if (!sessionId) return

    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
    const es = new EventSource(`${apiBaseUrl}/sessions/${sessionId}/events`, { withCredentials: true })
    eventSourceRef.current = es

    setIsConnected(true)
    setError(null)

    es.onmessage = (e) => {
      try {
        const parsed: AgentEvent = JSON.parse(e.data)
        setEvents((prev) => {
          const eventKey = `${parsed.ts}:${parsed.agent}:${parsed.step}:${parsed.message}`
          if (prev.some((item) => `${item.ts}:${item.agent}:${item.step}:${item.message}` === eventKey)) {
            return prev
          }
          return [...prev, parsed]
        })
        optionsRef.current.onEvent?.(parsed)

        if (parsed.step === 'session_done' || parsed.step === 'session_error') {
          setIsCompleted(true)
          optionsRef.current.onComplete?.()
          es.close()
        }
      } catch (err) {
        console.error('Failed to parse SSE event data', err)
      }
    }

    es.onerror = (err) => {
      console.warn('SSE connection error or closed', err)
      setIsConnected(false)
      optionsRef.current.onError?.(err)
      es.close()
    }

    return () => {
      es.close()
      setIsConnected(false)
    }
  }, [sessionId])

  return {
    events,
    isConnected,
    isCompleted,
    error,
    clearEvents,
  }
}

