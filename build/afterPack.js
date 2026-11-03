// Sets the exe icon + version info without Wine (pure JS via resedit).
const ResEdit = require('resedit'); const fs = require('fs'); const path = require('path');
exports.default = async (ctx) => {
  if (ctx.electronPlatformName !== 'win32') return;
  const name = ctx.packager.appInfo.productFilename, ver = ctx.packager.appInfo.version;
  const exePath = path.join(ctx.appOutDir, name + '.exe');
  const exe = ResEdit.NtExecutable.from(fs.readFileSync(exePath), { ignoreCert: true });
  const res = ResEdit.NtExecutableResource.from(exe);
  const ico = ResEdit.Data.IconFile.from(fs.readFileSync(path.join(__dirname, 'icon.ico')));
  const groups = ResEdit.Resource.IconGroupEntry.fromEntries(res.entries);
  ResEdit.Resource.IconGroupEntry.replaceIconsForResource(res.entries, groups.length ? groups[0].id : 1, groups.length ? groups[0].lang : 1033, ico.icons.map(i => i.data));
  const vi = ResEdit.Resource.VersionInfo.fromEntries(res.entries)[0] || ResEdit.Resource.VersionInfo.createEmpty();
  const [a, b, c] = ver.split('.').map(Number);
  vi.setFileVersion(a, b, c, 0, 1033); vi.setProductVersion(a, b, c, 0, 1033);
  vi.setStringValues({ lang: 1033, codepage: 1200 }, { ProductName: 'Desktop Pal', FileDescription: 'Desktop Pal', CompanyName: 'Desktop Pal', LegalCopyright: 'MIT License', OriginalFilename: name + '.exe', InternalName: 'Desktop Pal' });
  vi.outputToResourceEntries(res.entries);
  res.outputResource(exe);
  fs.writeFileSync(exePath, Buffer.from(exe.generate()));
  console.log('  • afterPack: icon + version info set on', exePath);
};
