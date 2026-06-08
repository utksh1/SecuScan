const fs = require('fs');

const originalRealpathSync = fs.realpathSync;
const originalRealpathSyncNative = fs.realpathSync.native;
const originalRealpath = fs.realpath;

function patchPath(path) {
  if (typeof path === 'string') {
    return path.replace(/D:\\GSSoC\\utksh1-SecuScan\\#561\\SecuScan/gi, 'Z:')
               .replace(/d:\\GSSoC\\utksh1-SecuScan\\#561\\SecuScan/gi, 'Z:')
               .replace(/D:\/GSSoC\/utksh1-SecuScan\/#561\/SecuScan/gi, 'Z:')
               .replace(/d:\/GSSoC\/utksh1-SecuScan\/#561\/SecuScan/gi, 'Z:');
  }
  return path;
}

fs.realpathSync = function(path, options) {
  const res = originalRealpathSync(path, options);
  return patchPath(res);
};

if (originalRealpathSyncNative) {
  fs.realpathSync.native = function(path, options) {
    const res = originalRealpathSyncNative(path, options);
    return patchPath(res);
  };
}

fs.realpath = function(path, options, callback) {
  let cb = callback;
  let opt = options;
  if (typeof options === 'function') {
    cb = options;
    opt = undefined;
  }
  originalRealpath(path, opt, (err, resolvedPath) => {
    if (err) {
      if (cb) cb(err);
      return;
    }
    if (cb) cb(null, patchPath(resolvedPath));
  });
};
console.log('FS Monkey-patch loaded successfully. Overriding #561 paths.');
