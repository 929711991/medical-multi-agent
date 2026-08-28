import { request } from '../utils/request'
import type { DoctorIdentity, LoginRequest } from '../types/auth'

export async function login(payload: LoginRequest): Promise<DoctorIdentity> {
  return (await request.post<{ user: DoctorIdentity }>('/auth/login', payload)).data.user
}
export async function logout(): Promise<void> { await request.post('/auth/logout') }
export async function getMe(): Promise<DoctorIdentity> { return (await request.get<DoctorIdentity>('/auth/me')).data }
