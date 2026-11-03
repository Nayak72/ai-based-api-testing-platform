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
  const seenIds = useRef(new Set<string>())
  const optionsRef = useRef(options)

  useEffect(() => {
    optionsRef.current = options
  }, [options])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  useEffect(() => {
    if (!sessionId) return
    seenIds.current.clear()

    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
    const es = new EventSource(`${apiBaseUrl}/sessions/${sessionId}/events`, { withCredentials: true })
    eventSourceRef.current = es

    setIsConnected(true)
    setError(null)

    es.onmessage = (e) => {
      try {
        const parsed: AgentEvent = JSON.parse(e.data)
        if (parsed.event_id && seenIds.current.has(parsed.event_id)) return
        if (parsed.event_id) seenIds.current.add(parsed.event_id)
        setEvents((prev) => {
          return [...prev, parsed]
        })
        optionsRef.current.onEvent?.(parsed)

        if (['session_done', 'session_error', 'session_cancelled'].includes(parsed.step)) {
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

