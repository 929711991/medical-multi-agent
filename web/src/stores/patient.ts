import { defineStore } from 'pinia'
import type { PatientSummary } from '../types/patient'

export const usePatientStore = defineStore('patient', {
  state: () => ({ current: null as PatientSummary | null }),
})
