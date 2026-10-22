// exFAT 드라이브(외장 SSD 등)에서 Node의 readlink가 일반 파일에 EINVAL 대신 EISDIR을 던져
// webpack 빌드가 실패하는 문제 보정. 다른 파일 시스템에서는 아무 영향 없음.
const fs = require("fs");

const fix = (err) => {
  if (err && err.code === "EISDIR" && err.syscall === "readlink") {
    err.code = "EINVAL";
    err.errno = -4071;
  }
  return err;
};

const { readlink, readlinkSync } = fs;
fs.readlink = function (path, options, cb) {
  if (typeof options === "function") [options, cb] = [undefined, options];
  return readlink.call(fs, path, options, (err, res) => cb(fix(err), res));
};
fs.readlinkSync = function (...args) {
  try {
    return readlinkSync.apply(fs, args);
  } catch (err) {
    throw fix(err);
  }
};
const p = fs.promises.readlink;
fs.promises.readlink = (...args) => p.apply(fs.promises, args).catch((err) => Promise.reject(fix(err)));
