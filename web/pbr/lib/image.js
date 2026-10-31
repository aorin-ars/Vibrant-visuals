// PNG and TGA reading and writing, with no library: the browser's (or Node's)
// own CompressionStream / DecompressionStream does the zlib part.
//
// Images are { width, height, data } with data a Uint8Array of straight
// (not premultiplied) RGBA. A canvas cannot be used to read them: it
// premultiplies alpha, which destroys the colour of transparent pixels -
// and a MERS map keeps its subsurface value in the alpha channel, so its
// metalness, emission and roughness would be lost wherever that is 0.
//
// Read: PNG of colour types 0, 2, 3, 4, 6 at any bit depth, interlaced or
// not, with tRNS; TGA types 1, 2, 3, 9, 10, 11 (colour-mapped, true-colour,
// grey, plain or run-length encoded), either origin. Converted the way
// Pillow's convert("RGBA") does it, which is what tools/build_pbr.py uses.

async function streamBytes(bytes, stream) {
  const out = new Response(new Blob([bytes]).stream().pipeThrough(stream));
  return new Uint8Array(await out.arrayBuffer());
}
export const inflate = (b) => streamBytes(b, new DecompressionStream("deflate"));
export const deflate = (b) => streamBytes(b, new CompressionStream("deflate"));
export const inflateRaw = (b) => streamBytes(b, new DecompressionStream("deflate-raw"));
export const deflateRaw = (b) => streamBytes(b, new CompressionStream("deflate-raw"));

// ---------------------------------------------------------------- CRC-32

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

export function crc32(bytes, crc = 0) {
  crc = ~crc >>> 0;
  for (let i = 0; i < bytes.length; i++) crc = CRC_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
  return ~crc >>> 0;
}

// ---------------------------------------------------------------- PNG

const PNG_SIG = [137, 80, 78, 71, 13, 10, 26, 10];
const ADAM7 = [ // x0, y0, dx, dy
  [0, 0, 8, 8], [4, 0, 8, 8], [0, 4, 4, 8], [2, 0, 4, 4],
  [0, 2, 2, 4], [1, 0, 2, 2], [0, 1, 1, 2],
];

function paeth(a, b, c) {
  const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
  return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
}

function unfilter(raw, offset, w, h, bpp, rowBytes) {
  // Returns the unfiltered rows of one (sub)image, and the offset after it.
  const out = new Uint8Array(rowBytes * h);
  for (let y = 0; y < h; y++) {
    const type = raw[offset++];
    const row = y * rowBytes, prev = row - rowBytes;
    for (let x = 0; x < rowBytes; x++) {
      const v = raw[offset++];
      const a = x >= bpp ? out[row + x - bpp] : 0;
      const b = y > 0 ? out[prev + x] : 0;
      const c = x >= bpp && y > 0 ? out[prev + x - bpp] : 0;
      let r;
      switch (type) {
        case 0: r = v; break;
        case 1: r = v + a; break;
        case 2: r = v + b; break;
        case 3: r = v + ((a + b) >> 1); break;
        case 4: r = v + paeth(a, b, c); break;
        default: throw new Error(`PNG: bad filter ${type}`);
      }
      out[row + x] = r & 0xff;
    }
  }
  return [out, offset];
}

export async function decodePNG(bytes) {
  for (let i = 0; i < 8; i++) if (bytes[i] !== PNG_SIG[i]) throw new Error("not a PNG");
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let pos = 8, width, height, depth, ctype, interlace, palette = null, trns = null;
  const idat = [];
  while (pos < bytes.length) {
    const len = dv.getUint32(pos);
    const type = String.fromCharCode(...bytes.subarray(pos + 4, pos + 8));
    const body = bytes.subarray(pos + 8, pos + 8 + len);
    pos += 12 + len;
    if (type === "IHDR") {
      const d = new DataView(body.buffer, body.byteOffset, body.byteLength);
      width = d.getUint32(0); height = d.getUint32(4);
      depth = body[8]; ctype = body[9]; interlace = body[12];
    } else if (type === "PLTE") palette = body;
    else if (type === "tRNS") trns = body;
    else if (type === "IDAT") idat.push(body);
    else if (type === "IEND") break;
  }
  const total = idat.reduce((s, b) => s + b.length, 0);
  const zdata = new Uint8Array(total);
  let o = 0;
  for (const b of idat) { zdata.set(b, o); o += b.length; }
  const raw = await inflate(zdata);

  const channels = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 }[ctype];
  if (!channels) throw new Error(`PNG: colour type ${ctype}`);
  const bitsPP = channels * depth;
  const bpp = Math.max(1, bitsPP >> 3);
  const out = new Uint8Array(width * height * 4);

  const sample = (row, x, c) => {
    // Sample c of pixel x in an unfiltered row, scaled to its own bit depth.
    if (depth === 8) return row[x * channels + c];
    if (depth === 16) return (row[(x * channels + c) * 2] << 8) | row[(x * channels + c) * 2 + 1];
    const bit = x * depth;                     // sub-byte depths have one channel
    return (row[bit >> 3] >> (8 - depth - (bit & 7))) & ((1 << depth) - 1);
  };
  const to8 = (v) => (depth === 16 ? v >> 8 : depth === 8 ? v : Math.round((v * 255) / ((1 << depth) - 1)));
  const trnsKey = (i) => (depth === 16 ? (trns[i * 2] << 8) | trns[i * 2 + 1] : (trns[i * 2] << 8) | trns[i * 2 + 1]);

  const put = (rows, rowBytes, w, h, x0, y0, dx, dy) => {
    for (let y = 0; y < h; y++) {
      const row = rows.subarray(y * rowBytes, (y + 1) * rowBytes);
      for (let x = 0; x < w; x++) {
        const p = ((y0 + y * dy) * width + (x0 + x * dx)) * 4;
        let r, g, b, a = 255;
        if (ctype === 3) {
          const i = sample(row, x, 0);
          r = palette[i * 3]; g = palette[i * 3 + 1]; b = palette[i * 3 + 2];
          if (trns && i < trns.length) a = trns[i];
        } else if (ctype === 0 || ctype === 4) {
          const v = sample(row, x, 0);
          r = g = b = to8(v);
          if (ctype === 4) a = to8(sample(row, x, 1));
          else if (trns && v === trnsKey(0)) a = 0;
        } else {
          const vr = sample(row, x, 0), vg = sample(row, x, 1), vb = sample(row, x, 2);
          r = to8(vr); g = to8(vg); b = to8(vb);
          if (ctype === 6) a = to8(sample(row, x, 3));
          else if (trns && vr === trnsKey(0) && vg === trnsKey(1) && vb === trnsKey(2)) a = 0;
        }
        out[p] = r; out[p + 1] = g; out[p + 2] = b; out[p + 3] = a;
      }
    }
  };

  if (!interlace) {
    const rowBytes = Math.ceil((width * bitsPP) / 8);
    const [rows] = unfilter(raw, 0, width, height, bpp, rowBytes);
    put(rows, rowBytes, width, height, 0, 0, 1, 1);
  } else {
    let offset = 0;
    for (const [x0, y0, dx, dy] of ADAM7) {
      const w = Math.ceil((width - x0) / dx), h = Math.ceil((height - y0) / dy);
      if (w <= 0 || h <= 0) continue;
      const rowBytes = Math.ceil((w * bitsPP) / 8);
      const [rows, next] = unfilter(raw, offset, w, h, bpp, rowBytes);
      offset = next;
      put(rows, rowBytes, w, h, x0, y0, dx, dy);
    }
  }
  return { width, height, data: out };
}

function chunk(type, body) {
  const out = new Uint8Array(12 + body.length);
  const dv = new DataView(out.buffer);
  dv.setUint32(0, body.length);
  for (let i = 0; i < 4; i++) out[4 + i] = type.charCodeAt(i);
  out.set(body, 8);
  dv.setUint32(8 + body.length, crc32(out.subarray(4, 8 + body.length)));
  return out;
}

// channels: 1 (grey, "L"), 3 (RGB) or 4 (RGBA); pixels interleaved, 8 bits.
export async function encodePNG(width, height, pixels, channels) {
  const ctype = { 1: 0, 3: 2, 4: 6 }[channels];
  const rowBytes = width * channels;
  const filtered = new Uint8Array((rowBytes + 1) * height);
  const cand = new Uint8Array(rowBytes);
  for (let y = 0; y < height; y++) {
    // Pick the filter with the smallest sum of absolute values, as libpng does.
    let best = 0, bestSum = Infinity;
    const row = y * rowBytes, prev = row - rowBytes;
    const dest = y * (rowBytes + 1);
    for (let type = 0; type < 5; type++) {
      let sum = 0;
      for (let x = 0; x < rowBytes; x++) {
        const v = pixels[row + x];
        const a = x >= channels ? pixels[row + x - channels] : 0;
        const b = y > 0 ? pixels[prev + x] : 0;
        const c = x >= channels && y > 0 ? pixels[prev + x - channels] : 0;
        const f = (type === 0 ? v : type === 1 ? v - a : type === 2 ? v - b
          : type === 3 ? v - ((a + b) >> 1) : v - paeth(a, b, c)) & 0xff;
        cand[x] = f;
        sum += f < 128 ? f : 256 - f;
      }
      if (sum < bestSum) {
        bestSum = sum; best = type;
        filtered[dest] = type;
        filtered.set(cand, dest + 1);
      }
    }
  }
  const ihdr = new Uint8Array(13);
  const dv = new DataView(ihdr.buffer);
  dv.setUint32(0, width); dv.setUint32(4, height);
  ihdr[8] = 8; ihdr[9] = ctype;
  const parts = [new Uint8Array(PNG_SIG), chunk("IHDR", ihdr),
    chunk("IDAT", await deflate(filtered)), chunk("IEND", new Uint8Array(0))];
  const out = new Uint8Array(parts.reduce((s, p) => s + p.length, 0));
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}

// ---------------------------------------------------------------- TGA

export function decodeTGA(bytes) {
  const idLen = bytes[0], cmapType = bytes[1], type = bytes[2];
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const cmapFirst = dv.getUint16(3, true), cmapLen = dv.getUint16(5, true), cmapBits = bytes[7];
  const width = dv.getUint16(12, true), height = dv.getUint16(14, true);
  const bits = bytes[16], desc = bytes[17];
  if (![1, 2, 3, 9, 10, 11].includes(type)) throw new Error(`TGA: type ${type}`);
  let pos = 18 + idLen;
  const cmapBytes = Math.ceil(cmapBits / 8);
  const cmap = cmapType ? bytes.subarray(pos, pos + cmapLen * cmapBytes) : null;
  pos += cmapType ? cmapLen * cmapBytes : 0;

  const pixBytes = Math.ceil(bits / 8);
  const count = width * height;
  let pix = bytes.subarray(pos, pos + count * pixBytes);
  if (type >= 9) {                                   // run-length encoded
    pix = new Uint8Array(count * pixBytes);
    let o = 0;
    while (o < pix.length && pos < bytes.length) {
      const head = bytes[pos++], n = (head & 0x7f) + 1;
      if (head & 0x80) {
        const v = bytes.subarray(pos, pos + pixBytes); pos += pixBytes;
        for (let i = 0; i < n && o < pix.length; i++) { pix.set(v, o); o += pixBytes; }
      } else {
        const len = Math.min(n * pixBytes, pix.length - o);
        pix.set(bytes.subarray(pos, pos + len), o); pos += n * pixBytes; o += len;
      }
    }
  }

  const colour = (src, bpp, off, outArr, p) => {
    // BGR(A) of bpp bits at src[off] into RGBA.
    if (bpp === 32) { outArr[p] = src[off + 2]; outArr[p + 1] = src[off + 1]; outArr[p + 2] = src[off]; outArr[p + 3] = src[off + 3]; }
    else if (bpp === 24) { outArr[p] = src[off + 2]; outArr[p + 1] = src[off + 1]; outArr[p + 2] = src[off]; outArr[p + 3] = 255; }
    else if (bpp === 16 || bpp === 15) {
      const v = src[off] | (src[off + 1] << 8);
      outArr[p] = ((v >> 10) & 31) * 255 / 31 | 0; outArr[p + 1] = ((v >> 5) & 31) * 255 / 31 | 0;
      outArr[p + 2] = (v & 31) * 255 / 31 | 0; outArr[p + 3] = 255;
    } else throw new Error(`TGA: ${bpp} bits`);
  };

  const out = new Uint8Array(count * 4);
  const topDown = (desc & 0x20) !== 0, rightToLeft = (desc & 0x10) !== 0;
  for (let y = 0; y < height; y++) {
    const sy = topDown ? y : height - 1 - y;
    for (let x = 0; x < width; x++) {
      const sx = rightToLeft ? width - 1 - x : x;
      const s = (sy * width + sx) * pixBytes, p = (y * width + x) * 4;
      if (type === 1 || type === 9) {
        const i = (pixBytes === 1 ? pix[s] : pix[s] | (pix[s + 1] << 8)) - cmapFirst;
        colour(cmap, cmapBits, i * cmapBytes, out, p);
      } else if (type === 3 || type === 11) {
        out[p] = out[p + 1] = out[p + 2] = pix[s]; out[p + 3] = pixBytes === 2 ? pix[s + 1] : 255;
      } else colour(pix, bits, s, out, p);
    }
  }
  return { width, height, data: out };
}

// Uncompressed 32-bit, top-left origin, 8 alpha bits.
export function encodeTGA(width, height, rgba) {
  const out = new Uint8Array(18 + width * height * 4);
  out[2] = 2;
  out[12] = width & 0xff; out[13] = width >> 8;
  out[14] = height & 0xff; out[15] = height >> 8;
  out[16] = 32; out[17] = 0x28;
  for (let i = 0, o = 18; i < width * height; i++, o += 4) {
    out[o] = rgba[i * 4 + 2]; out[o + 1] = rgba[i * 4 + 1];
    out[o + 2] = rgba[i * 4]; out[o + 3] = rgba[i * 4 + 3];
  }
  return out;
}

export async function decodeImage(name, bytes) {
  const lower = name.toLowerCase();
  if (lower.endsWith(".png")) return decodePNG(bytes);
  if (lower.endsWith(".tga")) return decodeTGA(bytes);
  throw new Error(`cannot read ${name}`);
}
