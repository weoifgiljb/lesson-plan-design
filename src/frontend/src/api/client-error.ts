export interface ApiError {
  code: string
  message: string
  details: Record<string, unknown>
  traceId: string
}

export class RequestError extends Error implements ApiError {
  code: string
  details: Record<string, unknown>
  traceId: string

  constructor(error: ApiError) {
    super(error.message)
    this.name = 'RequestError'
    this.code = error.code
    this.details = error.details
    this.traceId = error.traceId
  }
}

const FALLBACK: ApiError = {
  code: 'INTERNAL',
  message: '请求失败，请稍后重试',
  details: {},
  traceId: '',
}

export function toApiError(error: unknown): RequestError {
  if (error instanceof RequestError) return error
  const response = (error as { response?: { data?: Record<string, unknown> } })?.response
  const data = response?.data
  if (data && typeof data.code === 'string') {
    return new RequestError({
      code: data.code,
      message: typeof data.message === 'string' ? data.message : FALLBACK.message,
      details: (data.details as Record<string, unknown>) ?? {},
      traceId: typeof data.traceId === 'string' ? data.traceId : '',
    })
  }
  return new RequestError(FALLBACK)
}
