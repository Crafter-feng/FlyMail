/**
 * 版本号同步脚本
 *
 * 从项目根目录的 VERSION 文件读取版本号，同步到：
 * - package.json（根目录）
 * - frontend/package.json
 * - README.md 中的 version badge
 * - flymail/manifest（飞牛应用版本）
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


// 同步到飞牛应用 manifest（应用商店/安装包版本号）
const manifestPath = path.join(rootDir, 'flymail', 'manifest');
if (fs.existsSync(manifestPath)) {
  let manifest = fs.readFileSync(manifestPath, 'utf-8');
  const nextManifest = manifest.replace(
    /^version\s*=\s*\S+/m,
    (line) => line.replace(/=\s*\S+/, `= ${version}`),
  );
  if (nextManifest !== manifest) {
    fs.writeFileSync(manifestPath, nextManifest, 'utf-8');
    console.log('  ✓ flymail/manifest');
  } else if (/^version\s*=\s*/m.test(manifest)) {
    // 可能已一致：再校验是否等于目标版本
    const m = manifest.match(/^version\s*=\s*(\S+)/m);
    if (m && m[1] === version) {
      console.log('  · flymail/manifest 已一致');
    } else {
      console.error('  ✗ flymail/manifest 版本行无法更新');
      process.exit(1);
    }
  } else {
    console.error('  ✗ flymail/manifest 未找到 version 字段');
    process.exit(1);
  }
} else {
  console.error('  ✗ 未找到 flymail/manifest');
  process.exit(1);
}

console.log('版本号同步完成');
