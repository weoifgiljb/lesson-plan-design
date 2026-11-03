import { errorMessage } from './errors'

export interface ApiError {
  code: string
  message: string
  details: Record<string, unknown>
  traceId: string
  status: number
}

export class RequestError extends Error implements ApiError {
  code: string
  details: Record<string, unknown>
  traceId: string
  status: number

  constructor(error: ApiError) {
    super(error.message)
    this.name = 'RequestError'
    this.code = error.code
    this.details = error.details
    this.traceId = error.traceId
    this.status = error.status
  }
}

const FALLBACK: ApiError = {
  code: 'INTERNAL',
  message: '请求失败，请稍后重试',
  details: {},
  traceId: '',
  status: 0,
}

export function toApiError(error: unknown): RequestError {
  if (error instanceof RequestError) return error
  const response = (error as { response?: { data?: Record<string, unknown>; status?: number } })?.response
  const data = response?.data
  if (data && typeof data.code === 'string') {
    return new RequestError({
      code: data.code,
      message: errorMessage(
        data.code,
        typeof data.message === 'string' ? data.message : undefined,
      ),
      details: (data.details as Record<string, unknown>) ?? {},
      traceId: typeof data.traceId === 'string' ? data.traceId : '',
      status: typeof response?.status === 'number' ? response.status : 0,
    })
  }
  return new RequestError(FALLBACK)
}

export function isRequestError(error: unknown): error is RequestError {
  return error instanceof RequestError
}

export function isUnauthorized(error: unknown): boolean {
  return isRequestError(error) && error.status === 401
}

export function isForbidden(error: unknown): boolean {
  return isRequestError(error) && error.status === 403
}
