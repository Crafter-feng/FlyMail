/**
 * 版本号同步脚本
 *
 * 从项目根目录的 VERSION 文件读取版本号，同步到：
 * - package.json（根目录）
 * - frontend/package.json
 * - README.md 中的 version badge
 *
 * 用法：node scripts/sync-version.js
 */
const fs = require('fs');
const path = require('path');

const rootDir = path.join(__dirname, '..');
const versionFile = path.join(rootDir, 'VERSION');

// 读取版本号
const version = fs.readFileSync(versionFile, 'utf-8').trim();
if (!/^\d+\.\d+\.\d+/.test(version)) {
  console.error(`VERSION 文件内容非法: "${version}"`);
  process.exit(1);
}
console.log(`同步版本号: ${version}`);

// 同步到根目录 package.json
const rootPkgPath = path.join(rootDir, 'package.json');
const rootPkg = JSON.parse(fs.readFileSync(rootPkgPath, 'utf-8'));
rootPkg.version = version;
fs.writeFileSync(rootPkgPath, JSON.stringify(rootPkg, null, 2) + '\n', 'utf-8');
console.log('  ✓ package.json');

// 同步到 frontend/package.json
const frontendPkgPath = path.join(rootDir, 'frontend', 'package.json');
const frontendPkg = JSON.parse(fs.readFileSync(frontendPkgPath, 'utf-8'));
frontendPkg.version = version;
fs.writeFileSync(frontendPkgPath, JSON.stringify(frontendPkg, null, 2) + '\n', 'utf-8');
console.log('  ✓ frontend/package.json');

// 同步 README.md 中的 shields version badge
// 匹配: badge/version-x.y.z-...
const readmePath = path.join(rootDir, 'README.md');
if (fs.existsSync(readmePath)) {
  let readme = fs.readFileSync(readmePath, 'utf-8');
  const next = readme.replace(
    /badge\/version-\d+\.\d+\.\d+/g,
    `badge/version-${version}`,
  );
  if (next !== readme) {
    fs.writeFileSync(readmePath, next, 'utf-8');
    console.log('  ✓ README.md version badge');
  } else {
    console.log('  · README.md 无需更新（未找到 version badge 或已一致）');
  }
}

console.log('版本号同步完成');
