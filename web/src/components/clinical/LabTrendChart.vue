<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts/core'; import { LineChart } from 'echarts/charts'; import { GridComponent, TooltipComponent } from 'echarts/components'; import { CanvasRenderer } from 'echarts/renderers'
import type { LabResult } from '../../types/patient'
echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])
const props = defineProps<{ items: LabResult[] }>(); const el = ref<HTMLElement>(); let chart: echarts.ECharts | null = null
// 使用时间正序数据绘制检验趋势，重绘前释放旧实例避免重复占用容器。
function render() { if (!el.value) return; chart?.dispose(); chart = echarts.init(el.value); const values = [...props.items].reverse(); chart.setOption({ grid: { left: 45, right: 20, top: 20, bottom: 35 }, tooltip: { trigger: 'axis' }, xAxis: { type: 'category', data: values.map(i => i.observed_at.slice(5, 10)) }, yAxis: { type: 'value' }, series: [{ type: 'line', data: values.map(i => Number.parseFloat(i.value)), smooth: true, lineStyle: { color: '#0f9f95', width: 3 }, itemStyle: { color: '#0f9f95' } }] }) }
onMounted(render); watch(() => props.items, render); onBeforeUnmount(() => chart?.dispose())
</script><template><div ref="el" class="lab-chart" /></template><style scoped>.lab-chart { height: 280px; }</style>
