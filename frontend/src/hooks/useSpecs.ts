import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { specsApi, testCasesApi } from '../api/endpoints'

export function useSpecs(page = 1, pageSize = 20, status?: string) {
  return useQuery({
    queryKey: ['specs', page, pageSize, status],
    queryFn: () => specsApi.list({ page, page_size: pageSize, status }),
  })
}

export function useSpec(specId: string) {
  return useQuery({
    queryKey: ['spec', specId],
    queryFn: () => specsApi.get(specId),
    enabled: !!specId,
  })
}

export function useSpecEndpoints(specId: string) {
  return useQuery({
    queryKey: ['spec-endpoints', specId],
    queryFn: () => specsApi.endpoints(specId),
    enabled: !!specId,
  })
}

export function useUploadSpec() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ file, data }: { file: File; data: any }) => specsApi.upload(file, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['specs'] })
    },
  })
}

export function useParseSpec() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (specId: string) => specsApi.parse(specId),
    onSuccess: (_, specId) => {
      queryClient.invalidateQueries({ queryKey: ['spec', specId] })
      queryClient.invalidateQueries({ queryKey: ['spec-endpoints', specId] })
    },
  })
}

export function useDeleteSpec() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (specId: string) => specsApi.delete(specId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['specs'] })
    },
  })
}

export function useTestCases(specId: string, page = 1, pageSize = 50, endpointId?: string, category?: string) {
  return useQuery({
    queryKey: ['test-cases', specId, page, pageSize, endpointId, category],
    queryFn: () => testCasesApi.list(specId, { page, page_size: pageSize, endpoint_id: endpointId, category }),
    enabled: !!specId,
  })
}

export function useGenerateTestCases() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ specId, data }: { specId: string; data: any }) => testCasesApi.generate(specId, data),
    onSuccess: (_, { specId }) => {
      queryClient.invalidateQueries({ queryKey: ['test-cases', specId] })
    },
  })
}

export function useDeleteTestCase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ specId, testCaseId }: { specId: string; testCaseId: string }) => testCasesApi.delete(specId, testCaseId),
    onSuccess: (_, { specId }) => {
      queryClient.invalidateQueries({ queryKey: ['test-cases', specId] })
    },
  })
}