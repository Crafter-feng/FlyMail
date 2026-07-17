<template>
  <!-- 飞牛 NAS 授权目录/文件选择器：面包屑 + 逐级浏览 -->
  <div v-if="modelValue" class="nas-overlay" @click.self="onCancel">
    <div class="nas-modal">
      <div class="nas-head">
        <h4>{{ title }}</h4>
        <button type="button" class="nas-close" @click="onCancel" aria-label="关闭">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <!-- 面包屑 -->
      <div class="nas-nav">
        <span
          class="nav-item"
          :class="{ clickable: breadcrumbs.length > 0 }"
          @click="navigateToRoot"
        >授权目录</span>
        <template v-for="(b, i) in breadcrumbs" :key="i">
          <span class="nav-sep">/</span>
          <span class="nav-item clickable" @click="navigateTo(i)">{{ b.name }}</span>
        </template>
      </div>

      <!-- 列表 -->
      <div class="nas-list">
        <div v-if="loading" class="nas-empty">加载中...</div>
        <div v-else-if="dirs.length === 0 && files.length === 0" class="nas-empty">
          {{ breadcrumbs.length === 0
            ? '暂无可用授权目录，请先在飞牛应用设置中授权目录后重试'
            : (mode === 'file' ? '此目录下无子目录或文件' : '此目录下无子目录') }}
        </div>
        <template v-else>
          <!-- 子目录 -->
          <div
            v-for="dir in dirs"
            :key="'d-' + dir"
            class="nas-row dir"
            @click="enterDir(dir)"
          >
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
            <span>{{ pathBasename(dir) }}</span>
          </div>
          <!-- 文件（仅 file 模式） -->
          <div
            v-for="f in files"
            :key="'f-' + f.path"
            class="nas-row file"
            :class="{ selected: selectedFile === f.path }"
            @click="selectFile(f.path)"
            @dblclick="confirmFile(f.path)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <span class="file-name">{{ f.name }}</span>
            <span class="file-size">{{ formatSize(f.size) }}</span>
          </div>
        </template>
      </div>

      <div class="nas-foot">
        <span class="nas-path" :title="displayPath">{{ displayPath || '请选择' }}</span>
        <div class="nas-btns">
          <button type="button" class="btn-cancel" @click="onCancel">取消</button>
          <button
            type="button"
            class="btn-ok"
            :disabled="!canConfirm"
            @click="onConfirm"
          >确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import api from '../utils/api';

/** 选择器模式：dir=选目录（下载到 NAS / 备份），file=选文件（写信从 NAS 引用） */
const props = withDefaults(defineProps<{
  modelValue: boolean;
  mode?: 'dir' | 'file';
  title?: string;
}>(), {
  mode: 'dir',
  title: '选择目录',
});

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void;
  (e: 'confirm', path: string): void;
  (e: 'cancel'): void;
}>();

interface NasFileItem {
  name: string;
  path: string;
  size: number;
}

const loading = ref(false);
const dirs = ref<string[]>([]);
const files = ref<NasFileItem[]>([]);
const breadcrumbs = ref<{ name: string; path: string }[]>([]);
const currentPath = ref('');
const selectedFile = ref('');
const accessibleRoots = ref<string[]>([]);

const displayPath = computed(() => {
  if (props.mode === 'file') return selectedFile.value || currentPath.value;
  return currentPath.value;
});

const canConfirm = computed(() => {
  if (props.mode === 'file') return !!selectedFile.value;
  return !!currentPath.value;
});

function pathBasename(path: string): string {
  const parts = path.replace(/\\/g, '/').split('/').filter(Boolean);
  return parts[parts.length - 1] || path;
}

function formatSize(bytes: number): string {
  if (!bytes || bytes <= 0) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/** 打开时加载授权根目录 */
watch(() => props.modelValue, async (open) => {
  if (!open) return;
  breadcrumbs.value = [];
  currentPath.value = '';
  selectedFile.value = '';
  files.value = [];
  await loadRoots();
});

async function loadRoots() {
  loading.value = true;
  try {
    const data = await api.get('/backup/accessible-paths') as any;
    accessibleRoots.value = data.paths || [];
    dirs.value = accessibleRoots.value;
    files.value = [];
  } catch (e) {
    console.error('加载授权目录失败:', e);
    accessibleRoots.value = [];
    dirs.value = [];
  } finally {
    loading.value = false;
  }
}

async function loadChildren(path: string) {
  loading.value = true;
  try {
    const data = await api.get('/backup/accessible-paths/children', {
      params: {
        path,
        include_files: props.mode === 'file',
      },
    }) as any;
    dirs.value = data.dirs || [];
    files.value = (data.files || []) as NasFileItem[];
  } catch (e) {
    console.error('加载子目录失败:', e);
    dirs.value = [];
    files.value = [];
  } finally {
    loading.value = false;
  }
}

async function enterDir(dir: string) {
  const dirName = pathBasename(dir);
  if (accessibleRoots.value.includes(dir)) {
    breadcrumbs.value = [{ name: dirName, path: dir }];
  } else {
    breadcrumbs.value.push({ name: dirName, path: dir });
  }
  currentPath.value = dir;
  selectedFile.value = '';
  await loadChildren(dir);
}

function navigateToRoot() {
  if (breadcrumbs.value.length === 0) return;
  breadcrumbs.value = [];
  currentPath.value = '';
  selectedFile.value = '';
  dirs.value = accessibleRoots.value;
  files.value = [];
}

function navigateTo(idx: number) {
  breadcrumbs.value = breadcrumbs.value.slice(0, idx + 1);
  const path = breadcrumbs.value[idx].path;
  currentPath.value = path;
  selectedFile.value = '';
  loadChildren(path);
}

function selectFile(path: string) {
  selectedFile.value = path;
}

function confirmFile(path: string) {
  selectedFile.value = path;
  onConfirm();
}

function onConfirm() {
  if (!canConfirm.value) return;
  const path = props.mode === 'file' ? selectedFile.value : currentPath.value;
  emit('confirm', path);
  emit('update:modelValue', false);
}

function onCancel() {
  emit('cancel');
  emit('update:modelValue', false);
}
</script>

<style scoped>
.nas-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nas-modal {
  width: 90%;
  max-width: 560px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  overflow: hidden;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.nas-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.nas-head h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.nas-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  cursor: pointer;
}

.nas-close svg {
  width: 16px;
  height: 16px;
}

.nas-nav {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
  color: var(--text-secondary);
}

.nav-item.clickable {
  cursor: pointer;
  color: var(--accent-blue, #007AFF);
}

.nav-sep {
  margin: 0 4px;
  opacity: 0.5;
}

.nas-list {
  flex: 1;
  overflow-y: auto;
  min-height: 200px;
  max-height: 40vh;
  padding: 8px 0;
}

.nas-empty {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  line-height: 1.5;
}

.nas-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  cursor: pointer;
  color: var(--text-primary);
  font-size: 14px;
}

.nas-row:hover {
  background: var(--bg-hover, rgba(0, 0, 0, 0.04));
}

.nas-row.selected {
  background: rgba(0, 122, 255, 0.12);
}

.nas-row svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: var(--accent-blue, #007AFF);
}

.nas-row.file svg {
  color: var(--text-secondary);
}

.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 12px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.nas-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
}

.nas-path {
  flex: 1;
  font-size: 12px;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nas-btns {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.btn-cancel,
.btn-ok {
  padding: 6px 16px;
  border-radius: 8px;
  border: none;
  font-size: 13px;
  cursor: pointer;
}

.btn-cancel {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.btn-ok {
  background: var(--accent-blue, #007AFF);
  color: #fff;
}

.btn-ok:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
