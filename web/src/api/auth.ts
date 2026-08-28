import { request } from '../utils/request'
import type { DoctorIdentity, LoginRequest } from '../types/auth'

export async function login(payload: LoginRequest): Promise<DoctorIdentity> {
  /** 使用医生账号登录并返回当前身份。 */
  return (await request.post<{ user: DoctorIdentity }>('/auth/login', payload)).data.user
}
/** 清理当前登录会话。 */
export async function logout(): Promise<void> { await request.post('/auth/logout') }
/** 读取当前会话对应的医生身份。 */
export async function getMe(): Promise<DoctorIdentity> { return (await request.get<DoctorIdentity>('/auth/me')).data }
