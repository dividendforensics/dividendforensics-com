// Loads NORI/SUNNY/ROOM.pmx with their VMD motions and CAMERA_main.vmd in babylon-mmd and exposes
// seek(frame) / probe(frame, model, bones) for tools/mmd_check/babylon_render.mjs.
// build: npm i babylon-mmd@1.3.0 @babylonjs/core esbuild && esbuild babylon_entry.js --bundle --format=esm --outfile=bundle.js
import "babylon-mmd/esm/Loader/mmdModelLoader";
import "@babylonjs/core/Materials/standardMaterial";
import "@babylonjs/core/Materials/Textures/Loaders/envTextureLoader";
import "babylon-mmd/esm/Loader/pmxLoader";
import "babylon-mmd/esm/Loader/mmdOutlineRenderer";
import "babylon-mmd/esm/Runtime/Animation/mmdRuntimeCameraAnimation";
import "babylon-mmd/esm/Runtime/Animation/mmdRuntimeModelAnimation";
import { Engine } from "@babylonjs/core/Engines/engine";
import { Scene } from "@babylonjs/core/scene";
import { Vector3, Color3, Color4 } from "@babylonjs/core/Maths/math";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { MmdCamera } from "babylon-mmd/esm/Runtime/mmdCamera";
import { MmdRuntime } from "babylon-mmd/esm/Runtime/mmdRuntime";
import { VmdLoader } from "babylon-mmd/esm/Loader/vmdLoader";
import { MmdStandardMaterialProxy } from "babylon-mmd/esm/Runtime/mmdStandardMaterialProxy";

window.start = async (base) => {
  const canvas = document.getElementById("c");
  const engine = new Engine(canvas, true, { preserveDrawingBuffer: true, stencil: true });
  const scene = new Scene(engine);
  scene.clearColor = new Color4(0.1, 0.1, 0.1, 1);
  scene.ambientColor = new Color3(0.5, 0.5, 0.5);
  const camera = new MmdCamera("mmdCamera", new Vector3(0, 10, 0), scene);
  camera.minZ = 0.5; camera.maxZ = 2000;
  const light = new DirectionalLight("light", new Vector3(-0.5, -1, 0.5), scene);
  light.intensity = 1.0;
  const mmdRuntime = new MmdRuntime(scene);
  mmdRuntime.register(scene);
  const vmdLoader = new VmdLoader(scene);
  const camAnim = await vmdLoader.loadAsync("camera", base + "CAMERA_main.vmd");
  camera.setRuntimeAnimation(camera.createRuntimeAnimation(camAnim));
  mmdRuntime.addAnimatable(camera);
  const info = {};
  for (const name of ["ROOM", "NORI", "SUNNY"]) {
    const c = await LoadAssetContainerAsync(base + name + ".pmx", scene);
    c.addAllToScene();
    for (const m of c.meshes) m.alwaysSelectAsActiveMesh = true;
    const mesh = c.meshes[0];
    const model = mmdRuntime.createMmdModel(mesh, { materialProxyConstructor: MmdStandardMaterialProxy });
    const anim = await vmdLoader.loadAsync(name, base + name + ".vmd");
    model.setRuntimeAnimation(model.createRuntimeAnimation(anim));
    (window.__models ||= {})[name] = model;
    info[name] = { meshes: c.meshes.length, bones: model.runtimeBones.length, frames: anim.endFrame ?? null };
  }
  window.__scene = scene;
  window.probe = async (frame, model, names) => {
    await mmdRuntime.seekAnimation(frame, true);
    await scene.whenReadyAsync(); scene.render();
    const m = window.__models[model];
    const out = {};
    for (const b of m.runtimeBones) if (names.includes(b.name)) { const w = b.worldMatrix; out[b.name] = [w[12], w[13], w[14]]; }
    return out;
  };
  window.mats = () => scene.materials.slice(0, 12).map((m) => ({ n: m.name, cls: m.getClassName(), d: m.diffuseColor && m.diffuseColor.asArray(), a: m.ambientColor && m.ambientColor.asArray(), tex: m.diffuseTexture && m.diffuseTexture.name, ready: m.isReady ? null : null }));
  window.seek = async (frame) => {
    await mmdRuntime.seekAnimation(frame, true);
    await scene.whenReadyAsync();
    scene.render();
    scene.render();
    return { eye: camera.globalPosition.asArray(), fov: camera.fov, target: camera.target.asArray(), rot: camera.rotation.asArray(), dist: camera.distance };
  };
  return info;
};
