import { request } from '../utils/request'
import type { Allergy, ImagingReport, LabResult, Medication, Patient, PatientCreatePayload, PatientCreated, PatientOverview, PatientSummary, Visit } from '../types/patient'
import type { PageResult } from '../types/case'

export async function getPatients(params: { page: number; page_size: number; search?: string; sex?: string }): Promise<PageResult<Patient>> {
  /** 按分页和筛选条件读取患者列表。 */
  return (await request.get<PageResult<Patient>>('/patients', { params })).data
}
export async function createPatient(payload: PatientCreatePayload): Promise<PatientCreated> {
  /** 提交患者档案创建请求，并返回新患者编号。 */
  return (await request.post<PatientCreated>('/patients', payload)).data
}
/** 读取患者基础摘要。 */
export async function getPatient(id: string): Promise<PatientSummary> { return (await request.get<PatientSummary>(`/patients/${id}`)).data }
/** 读取患者概览页所需的聚合临床信息。 */
export async function getPatientOverview(id: string): Promise<PatientOverview> { return (await request.get<PatientOverview>(`/patients/${id}/overview`)).data }
/** 读取患者历史就诊记录。 */
export async function getVisits(id: string): Promise<Visit[]> { return (await request.get<{ items: Visit[] }>(`/patients/${id}/visits`)).data.items }
/** 读取患者检验结果。 */
export async function getLabs(id: string): Promise<LabResult[]> { return (await request.get<{ items: LabResult[] }>(`/patients/${id}/labs`)).data.items }
/** 读取患者影像报告。 */
export async function getImaging(id: string): Promise<ImagingReport[]> { return (await request.get<{ items: ImagingReport[] }>(`/patients/${id}/imaging`)).data.items }
/** 读取患者用药记录。 */
export async function getMedications(id: string): Promise<Medication[]> { return (await request.get<{ items: Medication[] }>(`/patients/${id}/medications`)).data.items }
/** 读取患者过敏记录。 */
export async function getAllergies(id: string): Promise<Allergy[]> { return (await request.get<{ items: Allergy[] }>(`/patients/${id}/allergies`)).data.items }
