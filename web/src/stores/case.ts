import { defineStore } from 'pinia'
import type { MedicalCase } from '../types/case'

export const useCaseStore = defineStore('case', {
  state: () => ({ current: null as MedicalCase | null }),
})
