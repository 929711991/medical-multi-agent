import { httpGet, httpPost } from '../service/http'
import type { Allergy, Department, ImagingReport, LabResult, Medication, Patient, PatientCreatePayload, PatientCreated, PatientOverview, PatientSummary, Visit } from '../types/patient'
import type { PageResult } from '../types/case'

export async function getPatients(params: { page: number; page_size: number; search?: string; sex?: string }): Promise<PageResult<Patient>> {
  /** 按分页和筛选条件读取患者列表。 */
  return httpGet<PageResult<Patient>>('/patients', params)
}
export async function createPatient(payload: PatientCreatePayload): Promise<PatientCreated> {
  /** 提交患者档案创建请求，并返回新患者编号。 */
  return httpPost<PatientCreated>('/patients', payload)
}
/** 读取患者基础摘要。 */
export async function getPatient(id: string): Promise<PatientSummary> { return httpGet<PatientSummary>(`/patients/${id}`) }
/** 读取患者概览页所需的聚合临床信息。 */
export async function getPatientOverview(id: string): Promise<PatientOverview> { return httpGet<PatientOverview>(`/patients/${id}/overview`) }
/** 读取患者历史就诊记录。 */
export async function getVisits(id: string): Promise<Visit[]> { return (await httpGet<{ items: Visit[] }>(`/patients/${id}/visits`)).items }
/** 读取可接诊科室字典。 */
export async function getDepartments(): Promise<Department[]> { return httpGet<Department[]>('/departments') }
/** 为已有患者创建新接诊。 */
export async function createVisit(id: string, payload: { department_code: string; chief_complaint: string; record?: Record<string, string | boolean> }): Promise<Visit> {
  return httpPost<Visit>(`/patients/${id}/visits`, payload)
}
/** 读取患者检验结果。 */
export async function getLabs(id: string): Promise<LabResult[]> { return (await httpGet<{ items: LabResult[] }>(`/patients/${id}/labs`)).items }
/** 读取患者影像报告。 */
export async function getImaging(id: string): Promise<ImagingReport[]> { return (await httpGet<{ items: ImagingReport[] }>(`/patients/${id}/imaging`)).items }
/** 读取患者用药记录。 */
export async function getMedications(id: string): Promise<Medication[]> { return (await httpGet<{ items: Medication[] }>(`/patients/${id}/medications`)).items }
/** 读取患者过敏记录。 */
export async function getAllergies(id: string): Promise<Allergy[]> { return (await httpGet<{ items: Allergy[] }>(`/patients/${id}/allergies`)).items }
