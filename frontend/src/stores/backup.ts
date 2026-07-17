import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '../utils/api';

/** 5个核心文件夹的固定定义（与 mailStore 一致）
 *
 * 切换邮箱时，文件夹名和顺序永远不变，只是 path 随 provider 不同而更新。
 * 后端返回的 IMAP 路径（含网易 &XfJT0ZAB- 等编码）会映射到这5个类别。
 */
const CORE_FOLDERS = [
  { name: '收件箱', path: 'INBOX' },
  { name: '已发送', path: 'Sent' },
  { name: '草稿箱', path: 'Drafts' },
  { name: '垃圾邮件', path: 'Junk' },
  { name: '已删除', path: 'Trash' },
];

/** 文件夹路径 → 颜色标识 class 映射 */
function getFolderClassByPath(path: string): string {
  const p = path.toLowerCase();
  if (p === 'inbox') return 'inbox';
  if (p === 'sent' || p.includes('sent')) return 'sent';
  if (p === 'drafts' || p.includes('draft')) return 'drafts';
  if (p === 'junk' || p.includes('junk') || p.includes('spam')) return 'junk';
  if (p === 'trash' || p.includes('trash') || p.includes('deleted')) return 'trash';
  return 'other';
}

export const useBackupStore = defineStore('backup', () => {
  /** 当前选中的文件夹路径（核心类别路径），从 sessionStorage 恢复 */
  const currentFolder = ref(sessionStorage.getItem('flymail_backup_folder') || 'INBOX');

  /** 各文件夹的归档数量映射：path → { count, deleted_count } */
  const folderCounts = ref<Record<string, { count: number; deleted_count: number }>>({});

  /** 固定5个核心文件夹列表（computed，永远不变，不会闪烁） */
  const folders = computed(() =>
  CORE_FOLDERS.map(f => ({
  folder: f.path,
  name: f.name,
  count: folderCounts.value[f.path]?.count || 0,
  deleted_count: folderCounts.value[f.path]?.deleted_count || 0,
  }))
  );

  /** 加载归档文件夹列表（后端按核心类别汇总返回5个文件夹）
  * @param accountId 筛选账号，为空则返回所有账号的文件夹汇总
  */
  async function loadFolders(accountId: string = '') {
  try {
  const params: Record<string, any> = {};
  if (accountId) params.account_id = accountId;
  const data = await api.get('/backup/folders', { params }) as any;
  // 后端返回5个核心文件夹的统计，映射到 folderCounts
  const counts: Record<string, { count: number; deleted_count: number }> = {};
  for (const f of (data.folders || [])) {
  counts[f.folder] = { count: f.count || 0, deleted_count: f.deleted_count || 0 };
  }
  folderCounts.value = counts;
  } catch (e) {
  console.error('加载备份文件夹失败:', e);
  }
  }

  /** 设置当前文件夹并持久化 */
  function setFolder(folder: string) {
  currentFolder.value = folder;
  sessionStorage.setItem('flymail_backup_folder', folder);
  }

  /** 文件夹路径转中文显示名（固定5个核心文件夹） */
  function folderDisplayName(folder: string): string {
  const f = CORE_FOLDERS.find(c => c.path === folder);
  return f ? f.name : folder;
  }

  /** 根据文件夹路径返回颜色标识 class */
  function getFolderClass(folder: string): string {
  return getFolderClassByPath(folder);
  }

  return {
  currentFolder,
  folders,
  loadFolders,
  setFolder,
  folderDisplayName,
  getFolderClass,
  };
});
