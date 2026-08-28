<script setup lang="ts">
import { computed } from 'vue'
import { riskLabels, statusLabels } from '../../utils/medical'
import type { RiskLevel } from '../../types/diagnosis'

const props = defineProps<{ type: 'risk' | 'status'; value?: string | null }>()
const label = computed(() => props.type === 'risk' ? riskLabels[props.value as RiskLevel] || '未分级' : statusLabels[props.value || ''] || '未知状态')
</script>
<template><span class="status-badge" :class="[type, value?.toLowerCase()]"><i />{{ label }}</span></template>
<style scoped lang="scss">
.status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 9px; border-radius: 99px; font-size: 12px; font-weight: 650; color: var(--text-secondary); background: #f1f3f6; white-space: nowrap; }
i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.low, .final { color: var(--risk-low); background: #ecfdf3; }
.medium, .waiting_review { color: var(--risk-medium); background: #fffaeb; }
.high { color: var(--risk-high); background: #fff4ed; }
.emergency, .failed { color: var(--risk-emergency); background: #fff1f2; }
.running { color: var(--primary); background: #eff6ff; }
.rejected { color: #7c3aed; background: #f5f3ff; }
</style>
