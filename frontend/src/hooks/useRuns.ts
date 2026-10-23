import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { runsApi, reportsApi } from '../api/endpoints'

export function useRuns(page = 1, pageSize = 20, specId?: string, status?: string) {
  return useQuery({
    queryKey: ['runs', page, pageSize, specId, status],
    queryFn: () => runsApi.list({ page, page_size: pageSize, spec_id: specId, status }),
  })
}

export function useRun(runId: string) {
  return useQuery({
    queryKey: ['run', runId],
    queryFn: () => runsApi.get(runId),
    enabled: !!runId,
  })
}

export function useRunResults(runId: string, page = 1, pageSize = 50, status?: string, category?: string) {
  return useQuery({
    queryKey: ['run-results', runId, page, pageSize, status, category],
    queryFn: () => runsApi.results(runId, { page, page_size: pageSize, status, category }),
    enabled: !!runId,
  })
}

export function useCreateRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { spec_id: string; name: string; config?: any }) => runsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] })
    },
  })
}

export function useCancelRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) => runsApi.cancel(runId),
    onSuccess: (_, runId) => {
      queryClient.invalidateQueries({ queryKey: ['run', runId] })
      queryClient.invalidateQueries({ queryKey: ['runs'] })
    },
  })
}

export function useRetryFailed() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) => runsApi.retryFailed(runId),
    onSuccess: (_, runId) => {
      queryClient.invalidateQueries({ queryKey: ['run', runId] })
      queryClient.invalidateQueries({ queryKey: ['run-results', runId] })
      queryClient.invalidateQueries({ queryKey: ['runs'] })
    },
  })
}

export function useAnalyzeRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) => runsApi.analyze(runId),
    onSuccess: (_, runId) => {
      queryClient.invalidateQueries({ queryKey: ['run-results', runId] })
    },
  })
}

export function useReports(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['reports', page, pageSize],
    queryFn: () => reportsApi.list({ page, page_size: pageSize }),
  })
}

export function useReportByRun(runId: string) {
  return useQuery({
    queryKey: ['report-by-run', runId],
    queryFn: () => reportsApi.getByRun(runId),
    enabled: !!runId,
  })
}

export function useGenerateReport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ runId, format }: { runId: string; format: 'html' | 'pdf' | 'both' }) => reportsApi.generate(runId, format),
    onSuccess: (_, { runId }) => {
      queryClient.invalidateQueries({ queryKey: ['report-by-run', runId] })
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}

export function useDownloadReport() {
  return useMutation({
    mutationFn: ({ reportId, format }: { reportId: string; format: 'html' | 'pdf' }) => reportsApi.download(reportId, format),
  })
}