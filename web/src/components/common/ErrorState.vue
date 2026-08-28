<script setup lang="ts">defineProps<{ message?: string }>(); defineEmits<{ retry: [] }>()</script>
<template><div class="error"><strong>暂时无法加载</strong><p>{{ message || '请稍后重试' }}</p><el-button @click="$emit('retry')">重新加载</el-button></div></template>
<style scoped>.error { padding: 36px; text-align: center; color: var(--text-secondary); }.error strong { color: var(--text-primary); }.error p { margin: 8px 0 16px; }</style>
