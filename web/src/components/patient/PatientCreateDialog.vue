<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createPatient, getDepartments } from '../../api/patient'
import type { Department } from '../../types/patient'
import { useAuthStore } from '../../stores/auth'
import { apiErrorMessage } from '../../utils/request'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; created: [patientId: string] }>()

const saving = ref(false)
const departments = ref<Department[]>([])
const departmentsLoading = ref(false)
const departmentsError = ref('')
const auth = useAuthStore()
const form = reactive({ name: '', sex: 'male', birth_date: '', department_code: '', chief_complaint: '', history: '' })

async function loadDepartments() {
  departmentsLoading.value = true
  departmentsError.value = ''
  try {
    departments.value = await getDepartments()
    const current = departments.value.find((item) => item.name === auth.user?.department)
    form.department_code ||= current?.code || departments.value[0]?.code || ''
  } catch (error) {
    departmentsError.value = apiErrorMessage(error, '科室列表加载失败')
  } finally {
    departmentsLoading.value = false
  }
}

watch(() => props.modelValue, (open) => { if (open && !departments.value.length) void loadDepartments() })

function disableFutureDate(value: Date) {
  // 日期选择器只允许今天及以前的出生日期。
  const today = new Date()
  today.setHours(23, 59, 59, 999)
  return value.getTime() > today.getTime()
}

function close() {
  // 通过双向绑定通知父页面关闭弹窗。
  emit('update:modelValue', false)
}

async function submit() {
  // 先在页面端清理输入，再提交后端进行同样的业务校验。
  if (!form.name.trim()) {
    ElMessage.warning('请输入患者姓名')
    return
  }
  if (!form.department_code) return ElMessage.warning('请选择本次接诊科室')
  if (!form.chief_complaint.trim()) return ElMessage.warning('请填写主要主诉')
  saving.value = true
  try {
    const result = await createPatient({
      name: form.name.trim(),
      sex: form.sex as 'male' | 'female' | 'other',
      birth_date: form.birth_date || null,
      history: form.history
        .split(/\n|；|;/)
        .map((item) => item.trim())
        .filter(Boolean),
      department_code: form.department_code,
      chief_complaint: form.chief_complaint.trim(),
    })
    ElMessage.success('患者创建成功')
    close()
    emit('created', result.patient_id)
    form.name = ''
    form.birth_date = ''
    form.history = ''
    form.chief_complaint = ''
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, '患者创建失败'))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog :model-value="props.modelValue" title="添加患者" width="560px" @close="close">
    <el-alert title="请仅录入已获授权且符合当前环境使用规范的患者信息" type="warning" :closable="false" show-icon />
    <el-form label-position="top" class="form" @submit.prevent="submit">
      <el-form-item label="姓名" required>
        <el-input v-model="form.name" maxlength="120" placeholder="例如：张某" />
      </el-form-item>
      <div class="grid">
        <el-form-item label="性别" required>
          <el-select v-model="form.sex" style="width: 100%">
            <el-option label="男" value="male" />
            <el-option label="女" value="female" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="出生日期">
          <el-date-picker
            v-model="form.birth_date"
            value-format="YYYY-MM-DD"
            type="date"
            :disabled-date="disableFutureDate"
            style="width: 100%"
            placeholder="请选择出生日期"
          />
        </el-form-item>
      </div>
      <el-form-item label="本次接诊科室" required>
        <el-select v-model="form.department_code" :loading="departmentsLoading" style="width: 100%" placeholder="请选择接诊科室">
          <el-option v-for="item in departments" :key="item.code" :label="item.name" :value="item.code" />
        </el-select>
        <el-alert v-if="departmentsError" :title="departmentsError" type="error" :closable="false">
          <el-button link type="primary" @click="loadDepartments">重试</el-button>
        </el-alert>
      </el-form-item>
      <el-form-item label="主要主诉" required>
        <el-input v-model="form.chief_complaint" type="textarea" :rows="3" maxlength="4000" show-word-limit placeholder="请描述本次就诊最主要的不适和持续时间" />
      </el-form-item>
      <el-form-item label="既往病史">
        <el-input v-model="form.history" type="textarea" :rows="4" placeholder="每行一条，例如：高血压病史5年" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="saving" @click="submit">保存并进入患者档案</el-button>
    </template>
  </el-dialog>
</template>

<style scoped lang="scss">
.form { margin-top: 18px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 680px) { .grid { grid-template-columns: 1fr; } }
</style>
