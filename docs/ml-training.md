# ML training for LAoN (cost-effective social stack)

LAoN uses vision ML in **two stages**. Detection/segmentation is **not** a replacement for similarity search.

```
User photo
  → [1] Crop / segment the sculpture   (this doc)
  → [2] Embed + vector match catalog   (existing pipeline)
  → [3] Possible matches + report
```

## Why not Google ML Kit for training?

| Tool | Role |
|---|---|
| **Google ML Kit** | On-device **inference** for stock tasks. Poor fit as a free custom-training lab for Nepali artifacts. |
| **rembg / edge crop (ML-0)** | **$0**, works now, focuses the frame without labels. |
| **Ultralytics YOLO detect/seg (ML-1)** | Free **custom training** on Colab; community boxes around artifacts. |
| **Roboflow free / Label Studio** | Free **annotation** UX for volunteers. |

Google ML Kit (or Core ML) can be a **later export target** (TFLite) once you have a trained ONNX/YOLO model — not the training framework.

## ML-0 — Zero-train crop (shipped in API)

`services/api/app/preprocess.py`:

1. **rembg** (optional): `pip install rembg onnxruntime` — U2Net background removal  
2. **edge_saliency** (default): Pillow + NumPy only — edge energy + center prior  

Match endpoint:

```
POST /api/match?crop=true
```

Response includes `crop.preview_jpeg_b64`, `crop.method`, `crop.bbox`.

Set `LAON_DISABLE_REMBG=1` to force the free edge crop even if rembg is installed.

## ML-1 — Community YOLO training (~$0)

### Label schema (v1)

Single class for maximum data efficiency:

| Class id | Name | Meaning |
|---|---|---|
| 0 | `artifact` | Main sculpture / stele / carving to match |

Optional later: `empty_niche`, then fine iconography classes.

### Folder layout

```
ml/
  configs/laon-artifact.yaml
  datasets/artifact/
    images/train/
    images/val/
    labels/train/     # YOLO txt: class cx cy w h (normalized)
    labels/val/
  notebooks/train_yolo_colab.ipynb
  weights/            # gitignored — put best.pt / best.onnx here locally
```

### Train free on Google Colab

1. Open `ml/notebooks/train_yolo_colab.ipynb` in Colab  
2. Enable GPU runtime  
3. Upload or mount a YOLO-format zip of `ml/datasets/artifact`  
4. Train YOLO11n-seg or YOLO11n detect for 50–100 epochs  
5. Download `best.pt` / export ONNX to `ml/weights/`  

Typical cost: **$0** on Colab free tier for nano models and small datasets (hundreds of images).

### Annotate without paying

- **Roboflow** free workspace → export YOLOv8/YOLO11 format  
- **Label Studio** or **CVAT** self-hosted for full OSS  

Invite diaspora/students to box sculptures in museum photos and community uploads (CC BY).

### License note (Ultralytics)

Ultralytics YOLO is **AGPL-3.0** unless you purchase a commercial license. LAoN is open-source; shipping training + serving code publicly is the intended AGPL-compatible path. Closed commercial forks need a commercial license or a different backbone.

## ML-2 — Fine classes (later)

After hundreds of labeled images per type, expand classes from catalog tags (`uma-mahesvara`, `padmapani`, …). Use scores only as **re-ranking hints**, never as legal identity.

## What success looks like

| Stage | Success |
|---|---|
| ML-0 | Messy gallery photos crop to the object; match UI shows “Focused region” |
| ML-1 | YOLO-n trained on community boxes beats edge crop on a held-out set |
| ML-2 | Optional class hint improves rank of correct deity type without claiming ownership |
