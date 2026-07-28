import { defineStore } from 'pinia';
import { computed, ref, watch } from 'vue';

/** 可展示全局搜索的列表视图 */
export type ListSearchView = 'mail' | 'unified' | 'backup';

const PLACEHOLDERS: Record<ListSearchView, string> = {
  mail: '搜索主题/发件人/收件人',
  unified: '搜索聚合邮件',
  backup: '搜索备份邮件',
};

/**
 * 列表搜索共享状态（顶栏搜索框）
 * - keyword：输入框即时值
 * - query：防抖后实际请求关键词
 * 搜索范围仍由各列表页自行决定（当前邮箱/聚合/备份）
 */
export const useListSearchStore = defineStore('listSearch', () => {
  const keyword = ref('');
  const query = ref('');
  /** 当前激活的可搜索视图；null 表示顶栏不显示搜索 */
  const activeView = ref<ListSearchView | null>(null);
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  const visible = computed(() => activeView.value !== null);
  const placeholder = computed(() =>
    activeView.value ? PLACEHOLDERS[activeView.value] : '搜索邮件',
  );
  const hasQuery = computed(() => !!query.value);

  function clearDebounce() {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
  }

  function commitFromKeyword() {
    const next = (keyword.value || '').trim();
    if (next === query.value) return;
    query.value = next;
  }

  /** 切换菜单时更新作用域；跨视图切换会清空关键词 */
  function setActiveView(view: ListSearchView | null) {
    if (activeView.value === view) return;
    activeView.value = view;
    // 切换菜单后清空，避免聚合/单邮箱/备份结果串台
    clear();
  }

  /** 回车立即搜索 */
  function flush() {
    clearDebounce();
    commitFromKeyword();
  }

  /** 清空时跳过 keyword watch，避免 clear 后又挂上 300ms 定时器 */
  let suppressKeywordWatch = false;

  /** 清空搜索（账号/文件夹切换、清除按钮、切菜单） */
  function clear() {
    clearDebounce();
    suppressKeywordWatch = true;
    keyword.value = '';
    if (query.value) {
      query.value = '';
    }
    suppressKeywordWatch = false;
    clearDebounce();
  }

  // 输入防抖 300ms（sync：保证 clear() 的 suppress 标志有效）
  watch(keyword, () => {
    if (suppressKeywordWatch) return;
    clearDebounce();
    debounceTimer = setTimeout(() => {
      commitFromKeyword();
    }, 300);
  }, { flush: 'sync' });

  return {
    keyword,
    query,
    activeView,
    visible,
    placeholder,
    hasQuery,
    setActiveView,
    flush,
    clear,
  };
});
