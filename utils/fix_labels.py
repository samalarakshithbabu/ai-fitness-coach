"""
fix_labels.py
-------------
Pads cls0 (deadlift) labels from 16 keypoints (53 cols) to 17 keypoints (56 cols)
by appending '0.0 0.0 0.0' for the missing keypoint.
Run once after prepare_dataset.py.
"""
from pathlib import Path

UNIFIED = Path(__file__).resolve().parent.parent / "dataset_unified"

fixed = 0
for split in ["train", "val"]:
    for f in (UNIFIED / "labels" / split).glob("cls0_*.txt"):
        lines = f.read_text().strip().splitlines()
        new_lines = []
        changed = False
        for line in lines:
            parts = line.split()
            if len(parts) == 53:          # 16 kpts → pad to 17
                parts += ["0.0", "0.0", "0.0"]
                changed = True
            new_lines.append(" ".join(parts))
        if changed:
            f.write_text("\n".join(new_lines) + "\n")
            fixed += 1

print(f"Fixed {fixed} label files.")
