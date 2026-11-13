import type { ApiResponse } from '@/types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly requestId?: string,
    public readonly code?: number | string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...init?.headers,
      },
    })
  } catch {
    throw new ApiError('无法连接服务，请确认后端已启动', 0, undefined, 'NETWORK_ERROR')
  }

  let payload: ApiResponse<T> | undefined
  try {
    payload = (await response.json()) as ApiResponse<T>
  } catch {
    throw new ApiError(
      response.ok ? '服务返回了无效数据' : `服务错误（${response.status}）`,
      response.status,
      response.headers.get('X-Request-ID') ?? undefined,
      'INVALID_RESPONSE',
    )
  }

  if (!response.ok || payload.code !== 0) {
    throw new ApiError(
      payload.message || '请求失败',
      response.status,
      payload.requestId ?? payload.request_id,
      payload.code,
    )
  }
  return payload
}

export async function requestNoContent(path: string, init?: RequestInit): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: 'include',
      headers: { ...init?.headers },
    })
  } catch {
    throw new ApiError('无法连接服务，请确认后端已启动', 0, undefined, 'NETWORK_ERROR')
  }
  if (!response.ok) {
    let message = '请求失败'
    let code: number | string | undefined
    let requestId = response.headers.get('X-Request-ID') ?? undefined
    try {
      const payload = (await response.json()) as Partial<ApiResponse<unknown>>
      message = payload.message || message
      code = payload.code
      requestId = payload.requestId ?? payload.request_id ?? requestId
    } catch {
      // A failed endpoint is allowed to return an empty body.
    }
    throw new ApiError(message, response.status, requestId, code)
  }
}
