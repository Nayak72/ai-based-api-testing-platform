import { useEffect, useRef, useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { runsApi, Run } from '../api/endpoints'

interface UsePollingOptions {
  enabled?: boolean
  interval?: number
  onStatusChange?: (status: string) => void
  onComplete?: (run: Run) => void
}

export function usePolling(runId: string | null, options: UsePollingOptions = {}) {
  const { enabled = true, interval = 2000, onStatusChange, onComplete } = options
  const queryClient = useQueryClient()
  const [isPolling, setIsPolling] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastStatusRef = useRef<string | null>(null)

  const poll = useCallback(async () => {
    if (!runId || !enabled) return

    try {
      const response = await runsApi.get(runId)
      const run = response.data

      if (run.status !== lastStatusRef.current) {
        lastStatusRef.current = run.status
        onStatusChange?.(run.status)
      }

      queryClient.setQueryData(['run', runId], run)
      queryClient.setQueryData(['runs'], (old: any) => {
        if (!old) return old
        return {
          ...old,
          runs: old.runs.map((r: Run) => r.id === runId ? run : r),
        }
      })

      if (['completed', 'completed_with_errors', 'failed', 'cancelled', 'cancelling'].includes(run.status)) {
        setIsPolling(false)
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
        onComplete?.(run)
      }
    } catch (error) {
      console.error('Polling error:', error)
    }
  }, [runId, enabled, queryClient, onStatusChange, onComplete])

  useEffect(() => {
    if (!runId || !enabled) {
      setIsPolling(false)
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    lastStatusRef.current = null
    setIsPolling(true)
    poll()

    intervalRef.current = setInterval(poll, interval)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      setIsPolling(false)
    }
  }, [runId, enabled, interval, poll])

  const stop = useCallback(() => {
    setIsPolling(false)
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const start = useCallback(() => {
    if (runId && enabled) {
      setIsPolling(true)
      poll()
      if (!intervalRef.current) {
        intervalRef.current = setInterval(poll, interval)
      }
    }
  }, [runId, enabled, interval, poll])

  return { isPolling, stop, start, poll }
}
