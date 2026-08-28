<script setup lang="ts">
import { computed, ref } from 'vue'; import type { LabResult } from '../../types/patient'; import { formatDateTime } from '../../utils/format'; import LabTrendChart from './LabTrendChart.vue'
const props = defineProps<{ items: LabResult[] }>(); const drawer = ref(false); const selectedName = ref(''); const selected = computed(() => props.items.filter(i => i.test_name === selectedName.value));
// 只有同一检验项目存在多个时间点时才打开趋势抽屉。
function open(item: LabResult) { if (props.items.filter(i => i.test_name === item.test_name).length < 2) return; selectedName.value = item.test_name; drawer.value = true }
</script>
<template><el-table :data="items" @row-click="open"><el-table-column prop="test_name" label="检验项目" min-width="170" /><el-table-column prop="value" label="结果" min-width="150" /><el-table-column prop="reference_range" label="参考范围" min-width="150" /><el-table-column label="异常状态" width="110"><template #default="{ row }"><span :class="['flag', row.abnormal_flag]">{{ row.abnormal_flag === 'high' ? '↑ 偏高' : row.abnormal_flag === 'low' ? '↓ 偏低' : '正常' }}</span></template></el-table-column><el-table-column label="检查时间" min-width="165"><template #default="{ row }">{{ formatDateTime(row.observed_at) }}</template></el-table-column></el-table><el-drawer v-model="drawer" :title="`${selectedName} · 历史趋势`" size="620px"><LabTrendChart :items="selected" /></el-drawer></template>
<style scoped>.flag { font-size: 12px; color: var(--risk-low); }.flag.high, .flag.low { color: var(--risk-high); font-weight: 650; }</style>
