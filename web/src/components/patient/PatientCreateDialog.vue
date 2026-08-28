<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createPatient } from '../../api/patient'
import { apiErrorMessage } from '../../utils/request'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; created: [patientId: string] }>()

const saving = ref(false)
const form = reactive({ name: '', sex: 'male', birth_date: '', history: '' })

function close() {
  emit('update:modelValue', false)
}

async function submit() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入患者姓名')
    return
  }
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
    })
    ElMessage.success('患者创建成功')
    close()
    emit('created', result.patient_id)
    form.name = ''
    form.birth_date = ''
    form.history = ''
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, '患者创建失败'))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog :model-value="props.modelValue" title="添加患者" width="560px" @close="close">
    <el-alert title="V1.1 仅允许录入虚构 DEMO 患者数据" type="warning" :closable="false" show-icon />
    <el-form label-position="top" class="form" @submit.prevent="submit">
      <el-form-item label="姓名" required>
        <el-input v-model="form.name" maxlength="120" placeholder="例如：DEMO 张某" />
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
          <el-date-picker v-model="form.birth_date" value-format="YYYY-MM-DD" type="date" style="width: 100%" />
        </el-form-item>
      </div>
      <el-form-item label="主要病史">
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
