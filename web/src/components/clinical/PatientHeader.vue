<script setup lang="ts">
import { computed } from 'vue'
import type { PatientSummary } from '../../types/patient'
import { sexLabel } from '../../utils/medical'
import { formatDate } from '../../utils/format'

const props = defineProps<{ patient: PatientSummary }>()
const age = computed(() => { if (!props.patient.birth_date) return null; const birth = new Date(props.patient.birth_date); const now = new Date(); return now.getFullYear() - birth.getFullYear() - (now < new Date(now.getFullYear(), birth.getMonth(), birth.getDate()) ? 1 : 0) })
</script>
<template><div class="patient-header"><div class="patient-avatar">{{ patient.demo_label?.slice(-1) || '患' }}</div><div><div class="name-row"><h1>{{ patient.demo_label }}</h1><span>DEMO</span></div><p><span class="mono">{{ patient.patient_id }}</span><i />{{ sexLabel(patient.sex) }}<i />{{ age ?? '—' }} 岁<i />出生日期 {{ formatDate(patient.birth_date) }}</p><div class="histories"><span v-for="item in patient.summary.history || []" :key="item">{{ item }}</span><span v-if="!patient.summary.history?.length">暂无主要慢性病记录</span></div></div><div class="actions"><slot /></div></div></template>
<style scoped lang="scss">
.patient-header { display: flex; align-items: center; gap: 16px; padding: 22px 24px; }.patient-avatar { width: 52px; height: 52px; border-radius: 14px; display: grid; place-items: center; background: #e8f0ff; color: var(--primary); font-weight: 800; }.name-row { display: flex; gap: 10px; align-items: center; }.name-row h1 { font-size: 21px; margin: 0; }.name-row span { padding: 2px 6px; border-radius: 4px; background: #ecfdf3; color: var(--risk-low); font-size: 10px; font-weight: 800; }.patient-header p { margin: 5px 0 8px; color: var(--text-secondary); font-size: 12px; display: flex; gap: 8px; align-items: center; }.patient-header p i { width: 3px; height: 3px; border-radius: 50%; background: var(--text-tertiary); }.histories { display: flex; gap: 6px; }.histories span { background: var(--soft-surface); color: var(--text-secondary); padding: 4px 8px; border-radius: 6px; font-size: 11px; }.actions { margin-left: auto; }
@media (max-width: 720px) { .patient-header { align-items: flex-start; flex-wrap: wrap; }.actions { width: 100%; margin: 0; }.patient-header p { flex-wrap: wrap; } }
</style>
