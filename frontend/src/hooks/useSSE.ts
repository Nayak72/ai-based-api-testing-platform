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

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  useEffect(() => {
    if (!sessionId) return

    const token = localStorage.getItem('access_token')
    if (!token) {
      setError('Not authenticated')
      return
    }

    const url = `/api/v1/sessions/${sessionId}/events?token=${encodeURIComponent(token)}`
    const es = new EventSource(url)
    eventSourceRef.current = es

    setIsConnected(true)
    setError(null)

    es.onmessage = (e) => {
      try {
        const parsed: AgentEvent = JSON.parse(e.data)
        setEvents((prev) => [...prev, parsed])
        options.onEvent?.(parsed)

        if (parsed.step === 'session_done' || parsed.step === 'session_error') {
          setIsCompleted(true)
          options.onComplete?.()
          es.close()
        }
      } catch (err) {
        console.error('Failed to parse SSE event data', err)
      }
    }

    es.onerror = (err) => {
      console.warn('SSE connection error or closed', err)
      setIsConnected(false)
      options.onError?.(err)
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

