// Minimal zip (.mcpack) writing and reading, with no library.
// Writing: deflate (or store, when that is smaller), UTF-8 names.
// Reading: stored and deflated entries; enough for a .mcpack.

import { crc32, deflateRaw, inflateRaw } from "./image.js";

const enc = new TextEncoder();

function dosTime(date) {
  const time = (date.getHours() << 11) | (date.getMinutes() << 5) | (date.getSeconds() >> 1);
  const day = ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
  return [time, day];
}

// files: iterable of [path, Uint8Array]. Returns the zip as a Uint8Array.
export async function writeZip(files, { onProgress } = {}) {
  const [time, day] = dosTime(new Date());
  const locals = [], central = [];
  let offset = 0, done = 0;
  const list = [...files];
  for (const [path, data] of list) {
    const name = enc.encode(path);
    const crc = crc32(data);
    let body = await deflateRaw(data), method = 8;
    if (body.length >= data.length) { body = data; method = 0; }

    const local = new Uint8Array(30 + name.length);
    const lv = new DataView(local.buffer);
    lv.setUint32(0, 0x04034b50, true); lv.setUint16(4, 20, true); lv.setUint16(6, 0x0800, true);
    lv.setUint16(8, method, true); lv.setUint16(10, time, true); lv.setUint16(12, day, true);
    lv.setUint32(14, crc, true); lv.setUint32(18, body.length, true); lv.setUint32(22, data.length, true);
    lv.setUint16(26, name.length, true);
    local.set(name, 30);

    const cen = new Uint8Array(46 + name.length);
    const cv = new DataView(cen.buffer);
    cv.setUint32(0, 0x02014b50, true); cv.setUint16(4, 20, true); cv.setUint16(6, 20, true);
    cv.setUint16(8, 0x0800, true); cv.setUint16(10, method, true); cv.setUint16(12, time, true);
    cv.setUint16(14, day, true); cv.setUint32(16, crc, true); cv.setUint32(20, body.length, true);
    cv.setUint32(24, data.length, true); cv.setUint16(28, name.length, true);
    cv.setUint32(42, offset, true);
    cen.set(name, 46);

    locals.push(local, body);
    central.push(cen);
    offset += local.length + body.length;
    if (onProgress) onProgress(++done, list.length);
  }
  const cenSize = central.reduce((s, c) => s + c.length, 0);
  const end = new Uint8Array(22);
  const ev = new DataView(end.buffer);
  ev.setUint32(0, 0x06054b50, true);
  ev.setUint16(8, central.length, true); ev.setUint16(10, central.length, true);
  ev.setUint32(12, cenSize, true); ev.setUint32(16, offset, true);
  const parts = [...locals, ...central, end];
  const out = new Uint8Array(offset + cenSize + 22);
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}

// Returns Map(path -> Uint8Array) of the files (not directories) in a zip.
export async function readZip(bytes) {
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let eocd = -1;
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65557); i--) {
    if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error("not a zip file");
  const count = dv.getUint16(eocd + 10, true);
  let p = dv.getUint32(eocd + 16, true);
  const dec = new TextDecoder();
  const files = new Map();
  for (let n = 0; n < count; n++) {
    if (dv.getUint32(p, true) !== 0x02014b50) throw new Error("broken zip directory");
    const method = dv.getUint16(p + 10, true);
    const csize = dv.getUint32(p + 20, true);
    const nameLen = dv.getUint16(p + 28, true), extraLen = dv.getUint16(p + 30, true);
    const commentLen = dv.getUint16(p + 32, true);
    const localOff = dv.getUint32(p + 42, true);
    const name = dec.decode(bytes.subarray(p + 46, p + 46 + nameLen));
    p += 46 + nameLen + extraLen + commentLen;
    if (name.endsWith("/")) continue;
    const lNameLen = dv.getUint16(localOff + 26, true), lExtraLen = dv.getUint16(localOff + 28, true);
    const start = localOff + 30 + lNameLen + lExtraLen;
    const body = bytes.subarray(start, start + csize);
    if (method === 0) files.set(name, body.slice());
    else if (method === 8) files.set(name, await inflateRaw(body));
    else throw new Error(`${name}: unsupported zip method ${method}`);
  }
  return files;
}
