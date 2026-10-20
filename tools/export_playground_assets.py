"""Reproducible handoff: original spectral NPZ + real checkpoint -> web SSI assets.

Examples (from repository root):
  python tools/export_playground_assets.py validate
  python tools/export_playground_assets.py sample --id PaviaU/sample_0008 \
    --source assets/lab/samples/paviau_0008.npz
  python tools/export_playground_assets.py model --id paviau \
    --checkpoint assets/lab/checkpoints/paviau_unet.pt \
    --sample assets/lab/samples/paviau_0008.npz
  python tools/export_playground_assets.py validate --require-complete

No model is marked ready until ONNX/PyTorch inference parity has been checked
and matching model/input files exist. This script does not train a model or
infer a spectral cube from an RGB/Atlas screenshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image
import torch

from hls import BAND_NAMES, HLS_MEAN, HLS_STD, TRAIN_MEAN_NORMALIZED, load_model, load_sample
from lab.adapters.extra import SPECS, _load_model
from lab.atlas_api import true_color

WEB = ROOT / "docs" / "playground"
MANIFEST = WEB / "compute-manifest.json"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def manifest_read() -> dict:
    data = json.loads(MANIFEST.read_text())
    if data.get("schema_version") != 1 or data.get("gallery_count") != 57:
        raise ValueError("Unsupported or incomplete browser manifest.")
    return data


def manifest_write(manifest: dict) -> None:
    temp = MANIFEST.with_suffix(".json.tmp")
    temp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    temp.replace(MANIFEST)


def model_entry(manifest: dict, model_id: str) -> dict:
    for model in manifest["models"]:
        if model["id"] == model_id:
            return model
    raise ValueError(f"Unknown model_id {model_id!r}.")


def sample_entry(manifest: dict, sample_id: str) -> dict:
    for sample in manifest["samples"]:
        if sample["id"] == sample_id:
            return sample
    raise ValueError(f"Unknown sample ID {sample_id!r}. Use the 57 exact Atlas IDs.")


def load_npz(model_id: str, source: Path):
    """Return original normalized C,H,W tensor, display RGB and fixed ROI labels."""
    if model_id == "hls-unet":
        raw, mask, x = load_sample(source)
        channels = list(BAND_NAMES)
        rgb = true_color(raw, (2, 1, 0))
        mean = TRAIN_MEAN_NORMALIZED.copy()
        zero = (-HLS_MEAN / HLS_STD).astype(np.float32)
        target_class = 1
        target_name = "Burn scar"
    else:
        spec = SPECS[model_id]
        with np.load(source, allow_pickle=False) as data:
            required = ("x", "mean", "std", "target_class")
            absent = [name for name in required if name not in data]
            if absent:
                raise ValueError("Missing NPZ keys: " + ", ".join(absent))
            x = np.asarray(data["x"], dtype=np.float32)
            raw_mean = np.asarray(data["mean"], dtype=np.float32)
            raw_std = np.asarray(data["std"], dtype=np.float32)
            target_class = int(data["target_class"])
            mask = np.asarray(data["label"], dtype=np.int64) if "label" in data else None
            rgb = np.asarray(data["rgb"]) if "rgb" in data else None
        if x.ndim != 3 or x.shape[0] != spec["in_channels"]:
            raise ValueError(f"{model_id} requires {spec['in_channels']} input bands.")
        if raw_mean.shape != (len(x),) or raw_std.shape != (len(x),) or \
                not np.all(np.isfinite(raw_std)) or np.any(raw_std <= 0):
            raise ValueError("The original per-channel mean/std are missing or invalid.")
        mean = np.zeros(len(x), dtype=np.float32)
        zero = np.asarray(-raw_mean / raw_std, dtype=np.float32)
        channels = list(spec["channels"])
        if target_class < 0 or target_class >= spec["n_classes"]:
            raise ValueError("Target class outside checkpoint class count.")
        if rgb is None:
            indices = (min(len(x)-1,round(len(x)*.68)),
                       min(len(x)-1,round(len(x)*.38)),
                       min(len(x)-1,round(len(x)*.12)))
            rgb = true_color(x*raw_std[:,None,None]+raw_mean[:,None,None], indices)
        sidecar = source.with_suffix(".json")
        target_name = spec["class_names"].get(target_class, f"Class {target_class}") \
                      if spec["kind"] == "seg" else f"Class {target_class}"
        if sidecar.is_file():
            target_name = str(json.loads(sidecar.read_text()).get("target_name", target_name))
    c,h,w = x.shape
    if h < 4 or w < 4 or not np.all(np.isfinite(x)):
        raise ValueError("Original model input must be finite C,H,W with H,W >= 4.")
    if rgb.shape != (h,w,3):
        raise ValueError(f"Aligned RGB preview must have shape {(h,w,3)}, got {rgb.shape}.")
    rgb = np.clip(rgb,0,255).astype(np.uint8)
    kind = "segmentation" if model_id=="hls-unet" or SPECS[model_id]["kind"]=="seg" else "classification"
    if kind=="segmentation":
        if mask is None or mask.shape != (h,w):
            raise ValueError("Every segmentation input requires the fixed ground-truth label map.")
        if not np.any(mask==target_class):
            raise ValueError("The fixed target ROI is empty.")
        if mask.min()<0 or mask.max()>255:
            raise ValueError("Segmentation class labels must fit in uint8.")
        mask=np.ascontiguousarray(mask,dtype=np.uint8)
    else:
        mask=None
    return dict(x=np.ascontiguousarray(x,dtype=np.float32),rgb=rgb,mask=mask,
                kind=kind,channels=channels,baseline_mean=mean,baseline_zero=zero,
                target_class=target_class,target_name=target_name)


def load_torch_model(model_id: str, checkpoint: Path):
    if model_id=="hls-unet":
        return load_model(checkpoint, torch.device("cpu"))
    spec=dict(SPECS[model_id])
    spec["checkpoint"]=checkpoint
    return _load_model(spec)


def expected_score(logits, data: dict, model_id: str) -> float:
    if data["kind"] == "classification":
        return float(logits[0,data["target_class"]])
    roi = data["mask"] == data["target_class"]
    return float(np.mean(logits[0,data["target_class"]][roi]))


def sample_export(sample_id: str, source: Path) -> dict:
    manifest=manifest_read()
    entry=sample_entry(manifest,sample_id)
    if entry.get("gallery_example") is False:
        raise ValueError("The bundled HLS example is already exported and verified.")
    model=model_entry(manifest,entry["model_id"])
    if not source.is_file():raise FileNotFoundError(source)
    # A convenient filename is not sufficient to prove which Atlas figure an
    # NPZ belongs to. Require provenance with a matching ID or sample index.
    provenance=source.with_suffix(".json")
    if not provenance.is_file():
        raise ValueError(
            f"Missing sample provenance {provenance}: provide atlas_id or original sample index."
        )
    identity=json.loads(provenance.read_text())
    digits=entry["id"].rsplit("sample_",1)[-1]
    if "atlas_id" in identity:
        if identity["atlas_id"]!=entry["id"]:
            raise ValueError("Source atlas_id disagrees with selected Atlas PNG.")
    elif "index" in identity:
        if not digits.isdigit() or int(identity["index"])!=int(digits):
            raise ValueError("Original dataset index disagrees with selected Atlas PNG.")
    else:
        raise ValueError("Sample provenance must include atlas_id or numeric index.")
    obj=load_npz(model["id"],source)
    paths=entry["required_assets"]
    rgb_path=WEB/paths["rgb"]
    tensor_path=WEB/paths["tensor"]
    mask_path=WEB/paths["mask"] if paths["mask"] else None
    meta_path=WEB/paths["metadata"]
    meta_path.parent.mkdir(parents=True,exist_ok=True)
    rgb_path.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(obj["rgb"],"RGB").save(rgb_path,"WEBP",quality=94,method=6)
    tensor_path.write_bytes(np.ascontiguousarray(obj["x"],dtype="<f4").tobytes())
    if mask_path:mask_path.write_bytes(obj["mask"].tobytes())

    model_instance=load_torch_model(model["id"],ROOT/model["checkpoint_repo_path"])
    with torch.inference_mode():
        actual=model_instance(torch.from_numpy(obj["x"][None]))
    original_score=expected_score(actual.detach().cpu().numpy(),obj,model["id"])
    metadata={
        "version":1,"sample_id":sample_id,"model_id":model["id"],
        "width":int(obj["x"].shape[2]),"height":int(obj["x"].shape[1]),
        "channels":obj["channels"],"target_class":obj["target_class"],
        "target_name":obj["target_name"],
        "target_kind":model["target_kind"],
        "region_pixels":int(np.count_nonzero(obj["mask"]==obj["target_class"])) if obj["mask"] is not None else None,
        "baseline_mean":obj["baseline_mean"].astype(float).tolist(),
        "baseline_zero":obj["baseline_zero"].astype(float).tolist(),
        "reference_full_score":original_score,
        "original_sample_sha256":digest(source),
        "original_checkpoint_sha256":digest(ROOT/model["checkpoint_repo_path"]),
        "files":{},
    }
    for key,path in (("tensor",tensor_path),("rgb",rgb_path),("mask",mask_path)):
        if path:
            metadata["files"][key]={"sha256":digest(path),"bytes":path.stat().st_size}
    meta_path.write_text(json.dumps(metadata,indent=2)+"\n")
    entry["files"]={"metadata":paths["metadata"],"tensor":paths["tensor"],
                    "rgb":paths["rgb"],"mask":paths["mask"]}
    entry["python_source"]=str(source.resolve().relative_to(ROOT)) if source.resolve().is_relative_to(ROOT) else None
    entry["source_sha256"]=digest(source)
    entry["provenance_sha256"]=digest(provenance)
    entry["status"]="ready" if model["onnx_state"]=="verified" and (WEB/model["onnx"]).is_file() else "awaiting_assets"
    manifest_write(manifest)
    return {"sample":sample_id,"status":entry["status"],"reference_full_score":original_score,
            "metadata":str(meta_path),"bytes":tensor_path.stat().st_size}


def model_export(model_id: str, checkpoint: Path, sample: Path) -> dict:
    import onnx
    import onnxruntime as ort
    manifest=manifest_read()
    entry=model_entry(manifest,model_id)
    if not checkpoint.is_file():raise FileNotFoundError(checkpoint)
    if not sample.is_file():raise FileNotFoundError(sample)
    data=load_npz(model_id,sample)
    torch.set_num_threads(4)
    model=load_torch_model(model_id,checkpoint).eval()
    dummy=torch.from_numpy(data["x"][None])
    with torch.inference_mode():
        original=model(dummy).cpu().numpy()
    path=WEB/entry["onnx"]
    path.parent.mkdir(parents=True,exist_ok=True)
    torch.onnx.export(model,dummy,str(path),opset_version=17,
                      input_names=["image"],output_names=["logits"],
                      dynamic_axes={"image":{0:"batch"},"logits":{0:"batch"}},
                      do_constant_folding=True,dynamo=False)
    onnx.checker.check_model(str(path))
    session=ort.InferenceSession(str(path),providers=["CPUExecutionProvider"])
    output=session.run(None,{"image":dummy.numpy()})[0]
    err=float(np.max(np.abs(output-original)))
    score=expected_score(output,data,model_id)
    if err>max(1e-3,float(np.max(np.abs(original)))*2e-4):
        raise ValueError(f"Unmasked ONNX/PyTorch parity failure: {err}")
    altered=data["x"].copy()
    altered[0,:max(1,altered.shape[1]//4),:max(1,altered.shape[2]//4)]=data["baseline_mean"][0]
    with torch.inference_mode():
        masked_pt=model(torch.from_numpy(altered[None])).cpu().numpy()
    masked_onnx=session.run(None,{"image":altered[None]})[0]
    masked_err=float(np.max(np.abs(masked_pt-masked_onnx)))
    if masked_err>max(1e-3,float(np.max(np.abs(masked_pt)))*2e-4):
        raise ValueError(f"Masked coalition ONNX/PyTorch parity failure: {masked_err}")
    entry["onnx_state"]="verified"
    entry["onnx_sha256"]=digest(path)
    entry["checkpoint_sha256"]=digest(checkpoint)
    entry["onnx_reference"]={"model_input_shape":list(dummy.shape),
                             "unmasked_score":score,"max_logit_error":err,
                             "masked_max_logit_error":masked_err}
    # Samples are only enabled after metadata and all input binaries also exist.
    for rec in manifest["samples"]:
        if rec["model_id"]!=model_id or rec.get("gallery_example") is False:
            continue
        files=rec.get("files",{})
        wanted=("metadata","tensor","rgb")
        has_inputs=all((WEB/files[k]).is_file() for k in wanted if k in files) and all(k in files for k in wanted)
        if entry["kind"]=="segmentation":
            has_inputs=has_inputs and bool(files.get("mask")) and (WEB/files["mask"]).is_file()
        if has_inputs:
            rec["status"]="ready"
    manifest_write(manifest)
    return {"model":model_id,"onnx":str(path),"bytes":path.stat().st_size,
            "sha256":entry["onnx_sha256"],"max_parity_error":err,"masked_error":masked_err}


def validate_manifest(*, complete: bool=False) -> dict:
    manifest=manifest_read()
    samples=[s for s in manifest["samples"] if s.get("image_url")]
    if len(samples)!=57 or len({s["id"] for s in samples})!=57:
        raise ValueError("The manifest must contain exactly 57 unique Atlas example IDs.")
    ready,pending=0,0
    for rec in manifest["samples"]:
        model=model_entry(manifest,rec["model_id"])
        if rec["status"]=="ready":
            if model["onnx_state"]!="verified" or not (WEB/model["onnx"]).is_file():
                raise ValueError(f"{rec['id']} is ready without a verified ONNX export.")
            for key in ("metadata","tensor","rgb"):
                if not rec.get("files",{}).get(key) or not (WEB/rec["files"][key]).is_file():
                    raise ValueError(f"{rec['id']} is ready but has no {key}.")
            if model["kind"]=="segmentation" and (not rec["files"].get("mask") or
                    not (WEB/rec["files"]["mask"]).is_file()):
                raise ValueError(f"{rec['id']} lacks its fixed target mask.")
            ready+=1
        else:
            pending+=1
    if complete and any(s["status"]!="ready" for s in samples):
        raise ValueError("Not all 57 Atlas examples have original verified compute assets.")
    return {"gallery_images":len(samples),"ready_samples":ready,
            "ready_gallery":sum(s["status"]=="ready" for s in samples),
            "pending":pending,"models_verified":
                [m["id"] for m in manifest["models"] if m["onnx_state"]=="verified"]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="cmd",required=True)
    s=sub.add_parser("sample",help="Export one original NPZ for its exact Atlas sample")
    s.add_argument("--id",required=True)
    s.add_argument("--source",required=True,type=Path)
    m=sub.add_parser("model",help="Export one compatible checkpoint to ONNX with measured parity")
    m.add_argument("--id",required=True)
    m.add_argument("--checkpoint",required=True,type=Path)
    m.add_argument("--sample",required=True,type=Path)
    v=sub.add_parser("validate",help="Audit registry without pretending unavailable models are ready")
    v.add_argument("--require-complete",action="store_true")
    args=parser.parse_args()
    if args.cmd=="sample":out=sample_export(args.id,args.source)
    elif args.cmd=="model":out=model_export(args.id,args.checkpoint,args.sample)
    else:out=validate_manifest(complete=args.require_complete)
    print(json.dumps(out,indent=2))


if __name__=="__main__":
    main()
