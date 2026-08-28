export interface DoctorIdentity {
  doctor_id: string
  name: string
  department: string
  title: string | null
  role: 'doctor'
}

export interface LoginRequest { account: string; password: string }
