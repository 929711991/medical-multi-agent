import { httpGet, httpPost } from '../../service/http'
import { isEmergency } from '../../utils/intake'

Page({
  data: { patients: [] as any[], selectedName: '', patientId: '', consultationId: '', messages: [] as any[], content: '', ready: false, emergency: false, canEscalate: false },
  async onLoad() { try { this.setData({ patients: await httpGet<any[]>('/patients') }) } catch (e: any) { wx.showToast({ title: e.detail, icon: 'none' }) } },
  selectPatient(event: any) { const patient = this.data.patients[Number(event.detail.value)]; this.setData({ patientId: patient.patient_id, selectedName: patient.name }) },
  content(event: any) { this.setData({ content: event.detail.value }) },
  async ensureConsultation() { if (this.data.consultationId) return this.data.consultationId; const item = await httpPost<any>('/consultations', { patient_id: this.data.patientId }); this.setData({ consultationId: item.id }); return item.id },
  async send() { if (!this.data.patientId) return wx.showToast({ title: '请先选择健康档案', icon: 'none' }); if (!this.data.content.trim()) return; try { const id = await this.ensureConsultation(); const result = await httpPost<any>(`/consultations/${id}/messages`, { client_message_id: `${Date.now()}`, content: this.data.content }); this.setData({ content: '', ready: result.intake.ready_for_analysis, emergency: isEmergency(result.intake.risk_level), canEscalate: isEmergency(result.intake.risk_level) }); this.setData({ messages: await httpGet<any[]>(`/consultations/${id}/messages`) }) } catch (e: any) { wx.showToast({ title: e.detail, icon: 'none' }) } },
  async analyze() { try { await httpPost(`/consultations/${this.data.consultationId}/analyze`); wx.showToast({ title: 'AI分析已提交' }) } catch (e: any) { wx.showToast({ title: e.detail, icon: 'none' }) } },
  async escalate() { try { await httpPost(`/consultations/${this.data.consultationId}/escalate`); wx.showToast({ title: '已转医生审核' }); this.setData({ canEscalate: false }) } catch (e: any) { wx.showToast({ title: e.detail, icon: 'none' }) } },
})
