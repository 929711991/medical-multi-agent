import { request } from '../../utils/request'

Page({
  data: { items: [] as any[], error: '', relations: ['self', 'father', 'mother', 'spouse', 'child', 'guardian', 'other'], form: { name: '', sex: 'other', relation_type: 'self', self_reported_history: [] as string[] } },
  onShow() { void this.load() },
  async load() { try { this.setData({ items: await request<any[]>('/patients'), error: '' }) } catch (e: any) { this.setData({ error: e.detail }) } },
  input(event: any) { this.setData({ 'form.name': event.detail.value }) },
  relation(event: any) { this.setData({ 'form.relation_type': this.data.relations[Number(event.detail.value)] }) },
  async create() { if (!this.data.form.name.trim()) return wx.showToast({ title: '请输入姓名', icon: 'none' }); try { await request('/patients', { method: 'POST', data: this.data.form }); this.setData({ 'form.name': '' }); await this.load() } catch (e: any) { wx.showToast({ title: e.detail, icon: 'none' }) } },
})
