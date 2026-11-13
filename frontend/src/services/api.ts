import { initialCheckins, initialGoals } from '@/mocks/data'
import type {
  ApiResponse,
  AuthenticatedUser,
  LoginPayload,
  RegisterPayload,
  StudyMateApi,
} from '@/types/api'
import { request } from '@/services/httpClient'

function response<T>(data: T, message = 'ok'): ApiResponse<T> {
  return {
    code: 0,
    message,
    data: structuredClone(data),
    requestId: `mock_${Date.now().toString(36)}`,
  }
}

function delay<T>(value: T, milliseconds = 380): Promise<T> {
  return new Promise((resolve) => window.setTimeout(() => resolve(value), milliseconds))
}

class StudyMateGateway implements StudyMateApi {
  login(payload: LoginPayload): Promise<ApiResponse<AuthenticatedUser>> {
    return request<AuthenticatedUser>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  register(payload: RegisterPayload): Promise<ApiResponse<AuthenticatedUser>> {
    return request<AuthenticatedUser>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  getGoals() {
    return delay(response(initialGoals))
  }

  getCheckins() {
    return delay(response(initialCheckins))
  }

}

/**
 * Account methods always use the real backend. Learning and matching API calls
 * live in studyData.ts, matchingData.ts and groups.ts.
 */
export const studyMateApi: StudyMateApi = new StudyMateGateway()
