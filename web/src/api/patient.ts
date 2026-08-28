import { request } from '../utils/request'
import type { Allergy, ImagingReport, LabResult, Medication, Patient, PatientCreatePayload, PatientCreated, PatientOverview, PatientSummary, Visit } from '../types/patient'
import type { PageResult } from '../types/case'

export async function getPatients(params: { page: number; page_size: number; search?: string; sex?: string }): Promise<PageResult<Patient>> {
  return (await request.get<PageResult<Patient>>('/patients', { params })).data
}
export async function createPatient(payload: PatientCreatePayload): Promise<PatientCreated> {
  return (await request.post<PatientCreated>('/patients', payload)).data
}
export async function getPatient(id: string): Promise<PatientSummary> { return (await request.get<PatientSummary>(`/patients/${id}`)).data }
export async function getPatientOverview(id: string): Promise<PatientOverview> { return (await request.get<PatientOverview>(`/patients/${id}/overview`)).data }
export async function getVisits(id: string): Promise<Visit[]> { return (await request.get<{ items: Visit[] }>(`/patients/${id}/visits`)).data.items }
export async function getLabs(id: string): Promise<LabResult[]> { return (await request.get<{ items: LabResult[] }>(`/patients/${id}/labs`)).data.items }
export async function getImaging(id: string): Promise<ImagingReport[]> { return (await request.get<{ items: ImagingReport[] }>(`/patients/${id}/imaging`)).data.items }
export async function getMedications(id: string): Promise<Medication[]> { return (await request.get<{ items: Medication[] }>(`/patients/${id}/medications`)).data.items }
export async function getAllergies(id: string): Promise<Allergy[]> { return (await request.get<{ items: Allergy[] }>(`/patients/${id}/allergies`)).data.items }
