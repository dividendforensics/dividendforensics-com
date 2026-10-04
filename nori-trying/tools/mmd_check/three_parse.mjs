import { readFileSync } from 'node:fs';
// Parses the exported PMX/VMD files with the MMDParser of three-mmd-loader (github.com/takahirox/three-mmd-loader).
// usage: node tools/mmd_check/three_parse.mjs <mmd dir> <three-mmd-loader checkout>
const [,, d, tml] = process.argv;
const { MMDParser } = await import(`${tml}/src/libs/mmdparser.module.js`);
const p = new MMDParser.Parser();
const ab = (f) => { const b = readFileSync(`${d}/${f}`); return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength); };
for (const m of ['NORI', 'SUNNY', 'ROOM']) {
  const pmx = p.parsePmx(ab(`${m}.pmx`), true);
  const vmd = p.parseVmd(ab(`${m}.vmd`), true);
  const names = new Set(pmx.bones.map((b) => b.name));
  const missing = vmd.motions.filter((k) => !names.has(k.boneName)).length;
  console.log(m, JSON.stringify({ name: pmx.metadata.modelName, v: pmx.metadata.vertexCount, faces: pmx.metadata.faceCount, mats: pmx.metadata.materialCount, bones: pmx.metadata.boneCount, morphs: pmx.metadata.morphCount, frames: pmx.metadata.frameCount, tex: pmx.textures.length, vmdModel: vmd.metadata.name, boneKeys: vmd.metadata.motionCount, morphKeys: vmd.metadata.morphCount, keysWithUnknownBone: missing }));
}
const cam = p.parseVmd(ab('CAMERA_main.vmd'), true);
console.log('CAMERA', cam.metadata.name, cam.metadata.cameraCount, JSON.stringify(cam.cameras[0]));
