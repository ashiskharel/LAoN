# LAoN ML — crop & train

Cost-effective vision stack for a social heritage project.

| Phase | What | Cost |
|---|---|---|
| **ML-0** | Crop before match (`rembg` optional + edge saliency) | $0 |
| **ML-1** | Train YOLO `artifact` detector/segmenter on community labels | $0 (Colab free GPU) |
| **ML-2** | Fine iconography classes | $0 compute; volunteer labels |

See [docs/ml-training.md](../docs/ml-training.md) for the full guide.

## Quick start — training (ML-1)

1. Put images in `datasets/artifact/images/train` and `.../val`  
2. Put YOLO labels in `datasets/artifact/labels/train` and `.../val`  
3. Open `notebooks/train_yolo_colab.ipynb` on Google Colab with GPU  
4. Or locally (needs GPU for speed):

```bash
pip install ultralytics
yolo segment train data=ml/configs/laon-artifact.yaml model=yolo11n-seg.pt epochs=80 imgsz=640
```

5. Copy `runs/.../weights/best.pt` → `ml/weights/laon-artifact.pt` (gitignored)

## Label format (YOLO)

Each `labels/train/foo.txt` line:

```
0 0.50 0.48 0.62 0.80
```

= class `artifact`, center x/y, width/height (normalized 0–1).

## Ethics

Crops and class scores **assist matching**. They are not proof of ownership or a legal claim. Only rights-cleared images belong in the public dataset.
