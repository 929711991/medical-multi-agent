import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { describe, expect, it } from 'vitest'
import StatusBadge from '../src/components/common/StatusBadge.vue'
import ConditionCard from '../src/components/diagnosis/ConditionCard.vue'
import DiagnosisResult from '../src/components/diagnosis/DiagnosisResult.vue'
import DoctorReviewDrawer from '../src/components/diagnosis/DoctorReviewDrawer.vue'
import type { DiagnosisResult as DiagnosisResultType } from '../src/types/diagnosis'

const result: DiagnosisResultType = {
  clinical_summary: '活动后胸痛，需要结合临床进一步评估。',
  key_findings: ['活动后胸痛', '高血压病史'],
  possible_conditions: [{ name: '心源性胸痛待鉴别', reason: '症状与活动相关', confidence: 0.72 }],
  red_flags: [],
  missing_information: ['是否伴冷汗'],
  recommended_tests: ['复查心电图'],
  recommended_department: '心内科',
  risk_level: 'high',
  specialist_opinions: [],
  evidence: [],
  rag_enabled: false,
  disclaimer: '仅供医生辅助决策。',
}

describe('clinical result components', () => {
  it('renders a textual high-risk badge, not color alone', () => {
    const wrapper = mount(StatusBadge, { props: { type: 'risk', value: 'high' } })
    expect(wrapper.text()).toContain('高风险')
    expect(wrapper.classes()).toContain('high')
  })

  it('converts confidence into a clinical support label', () => {
    const wrapper = mount(ConditionCard, { props: { condition: result.possible_conditions[0], index: 0 } })
    expect(wrapper.text()).toContain('较强支持')
    expect(wrapper.text()).not.toContain('72%')
  })

  it('renders structured diagnosis fields and RAG-safe content', () => {
    const wrapper = mount(DiagnosisResult, { props: { result } })
    expect(wrapper.text()).toContain(result.clinical_summary)
    expect(wrapper.text()).toContain('需要进一步确认')
    expect(wrapper.text()).toContain('复查心电图')
  })

  it('submits an edit with the expected assessment version', async () => {
    const wrapper = mount(DoctorReviewDrawer, {
      props: { modelValue: false, result, version: 3 },
      global: { plugins: [ElementPlus] },
      attachTo: document.body,
    })
    await wrapper.setProps({ modelValue: true })
    await new Promise((resolve) => setTimeout(resolve, 0))
    const submit = [...document.querySelectorAll('button')].find((button) =>
      button.textContent?.includes('提交修改并确认'),
    ) as HTMLButtonElement
    submit.click()
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('submit')?.[0]?.[0]).toMatchObject({ action: 'edit', expected_version: 3 })
    wrapper.unmount()
  })
})
