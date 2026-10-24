"""Build scripts/portrait.json from a photo: cut out the person, boost contrast, map to ASCII.

Run locally (not in CI). Needs the U^2-Net human model:
  curl -L -o u2net_human_seg.onnx https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx
  uv run --with onnxruntime --with numpy --with pillow python scripts/make_portrait.py photo.jpg u2net_human_seg.onnx
"""
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime
from PIL import Image, ImageFilter, ImageOps

from artwork import RAMP

COLS = 76
CELL_ASPECT = .57  # glyph width / line step in the card (4.8px / 8.4px)
HEAD = 1.15  # keep head and shoulders: crop height as a multiple of the cutout width
GAMMA = .55  # lift shadows so dark hair and clothing still read as dense glyphs


def person_mask(image, model):
    session = onnxruntime.InferenceSession(model)
    x = np.asarray(image.resize((320, 320), Image.LANCZOS), dtype=np.float32) / 255
    x = ((x - [.485, .456, .406]) / [.229, .224, .225]).transpose(2, 0, 1)[None].astype(np.float32)
    pred = session.run(None, {session.get_inputs()[0].name: x})[0][0, 0]
    pred = (pred - pred.min()) / (pred.max() - pred.min())
    return Image.fromarray((pred * 255).astype(np.uint8)).resize(image.size, Image.LANCZOS)


def main(photo, model):
    image = Image.open(photo).convert("RGB")
    alpha = person_mask(image, model)
    left, top, right, bottom = alpha.point(lambda v: 255 if v > 110 else 0).getbbox()
    box = (left, top, right, min(bottom, top + int((right - left) * HEAD)))
    image, alpha = image.crop(box), alpha.crop(box)
    gray = ImageOps.autocontrast(image.convert("L").filter(ImageFilter.UnsharpMask(2, 160, 2)), cutoff=2, mask=alpha)
    gray = gray.point(lambda v: int(255 * (v / 255) ** GAMMA))
    rows = round(COLS * image.height / image.width * CELL_ASPECT)
    gray, alpha = gray.resize((COLS, rows), Image.LANCZOS), alpha.resize((COLS, rows), Image.LANCZOS)
    lines = ["".join(" " if alpha.getpixel((x, y)) < 110 else RAMP[1 + gray.getpixel((x, y)) * (len(RAMP) - 2) // 255]
                     for x in range(COLS)).rstrip() for y in range(rows)]
    target = Path(__file__).with_name("portrait.json")
    eyes = json.loads(target.read_text(encoding="utf-8"))["eyes"]
    target.write_text(json.dumps({"rows": lines, "eyes": eyes}, indent=1), encoding="utf-8")
    print("\n".join(f"{i:2d} {row}" for i, row in enumerate(lines)))


if __name__ == "__main__":
    main(*sys.argv[1:3])
