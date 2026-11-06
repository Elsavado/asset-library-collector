// node figmod.js in.fig out.fig seed  — re-colours a Figma canvas (fig-kiwi): every colour's hue turns by an angle
// taken from the seed, so the design keeps its layout and text but is a new variant. Prints the number of colours.
const fs = require("fs"), kiwi = require("kiwi-schema"), pako = require("pako"), fzstd = require("fzstd");
const [, , inp, out, seed] = process.argv;
const buf = fs.readFileSync(inp);
if (buf.toString("latin1", 0, 8) !== "fig-kiwi") { console.error("not fig-kiwi"); process.exit(2); }
const head = buf.subarray(0, 12), chunks = [];
for (let o = 12; o + 4 <= buf.length;) { const n = buf.readUInt32LE(o); chunks.push(buf.subarray(o + 4, o + 4 + n)); o += 4 + n; }
const unz = c => (c[0] === 0x28 && c[1] === 0xb5 && c[2] === 0x2f && c[3] === 0xfd) ? fzstd.decompress(c) : pako.inflateRaw(c);
const schemaBin = unz(chunks[0]);
const schema = kiwi.compileSchema(kiwi.decodeBinarySchema(schemaBin));
const msg = schema.decodeMessage(unz(chunks[1]));
let h = 0; for (const ch of String(seed)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
const turn = 40 + (h % 280);  // 40..319 degrees
function rot(c) {
  const r = c.r, g = c.g, b = c.b, mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
  if (mx - mn < 1e-6) return false;  // greys stay
  const d = mx - mn, s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
  let hu = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  hu = ((hu * 60 + turn) % 360) / 360;
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
  const f = t => { t = (t + 1) % 1; return t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p; };
  c.r = f(hu + 1 / 3); c.g = f(hu); c.b = f(hu - 1 / 3); return true;
}
let n = 0;
(function walk(o) {
  if (!o || typeof o !== "object" || ArrayBuffer.isView(o)) return;
  if (typeof o.r === "number" && typeof o.g === "number" && typeof o.b === "number" && typeof o.a === "number") { if (rot(o)) n++; return; }
  for (const k in o) walk(o[k]);
})(msg);
const data = pako.deflateRaw(schema.encodeMessage(msg));
const parts = [head];
const put = c => { const l = Buffer.alloc(4); l.writeUInt32LE(c.length); parts.push(l, Buffer.from(c)); };
put(pako.deflateRaw(schemaBin)); put(data); for (const c of chunks.slice(2)) put(c);
fs.writeFileSync(out, Buffer.concat(parts));
console.log(n);
