"""
audit_dataset.py
----------------
Scans dataset_unified/labels/train and reports:
  - Per-class frame counts
  - Imbalance ratio (max / min)
  - Empty label files (frames with no annotation)
  - Recommended minimum samples per class

Usage:
    python utils/audit_dataset.py
"""

from pathlib import Path
from collections import Counter, defaultdict

ROOT      = Path(__file__).resolve().parent.parent
LABEL_DIR = ROOT / "dataset_unified" / "labels" / "train"

# Must match CLASS_NAMES in main.py
CLASS_NAMES = {
    0:  "deadlift",
    1:  "lateral_raise",
    2:  "squat",
    3:  "front_squat",
    4:  "zercher_squat",
    5:  "romanian_deadlift",
    6:  "sumo_deadlift",
    7:  "bench_press",
    8:  "incline_bench_press",
    9:  "decline_bench_press",
    10: "barbell_biceps_curl",
    11: "hammer_curl",
    12: "shoulder_press",
    13: "lat_pulldown",
    14: "pull_up",
    15: "push_up",
    16: "leg_extension",
    17: "leg_raises",
    18: "hip_thrust",
    19: "plank",
    20: "tricep_dips",
    21: "tricep_pushdown",
    22: "t_bar_row",
    23: "russian_twist",
    24: "chest_fly_machine",
}

RECOMMENDED_MIN = 400   # minimum frames per class for reliable training


def audit():
    if not LABEL_DIR.exists():
        print(f"[ERROR] Label directory not found: {LABEL_DIR}")
        print("        Run utils/prepare_dataset.py first.")
        return

    class_counts: Counter = Counter()
    empty_files:  list    = []
    annotation_counts: defaultdict = defaultdict(int)

    for txt_file in LABEL_DIR.glob("*.txt"):
        content = txt_file.read_text().strip()
        if not content:
            empty_files.append(txt_file.name)
            continue
        for line in content.splitlines():
            parts = line.split()
            if parts:
                cls_id = int(parts[0])
                class_counts[cls_id] += 1
                annotation_counts[cls_id] += 1

    print("\n" + "=" * 60)
    print("  DATASET AUDIT REPORT")
    print("=" * 60)

    if not class_counts:
        print("[WARN] No annotations found. Check label files.")
        return

    max_count = max(class_counts.values())
    min_count = min(class_counts.values())
    imbalance = max_count / max(min_count, 1)

    print(f"\nTotal annotated frames : {sum(class_counts.values())}")
    print(f"Classes found          : {len(class_counts)}")
    print(f"Imbalance ratio        : {imbalance:.1f}x  (max/min)")
    print(f"Empty label files      : {len(empty_files)}")
    print()

    print(f"{'Class':<25} {'Count':>6}  {'Bar':<22}  {'Status'}")
    print("-" * 65)
    for cls_id in sorted(class_counts.keys()):
        name  = CLASS_NAMES.get(cls_id, f"class_{cls_id}")
        count = class_counts[cls_id]
        bar   = "█" * int(22 * count / max_count)
        status = "OK" if count >= RECOMMENDED_MIN else f"LOW — need {RECOMMENDED_MIN - count} more"
        print(f"  {name:<23} {count:>6}  {bar:<22}  {status}")

    # Classes in CLASS_NAMES but not in dataset
    missing = [
        f"  {CLASS_NAMES[i]} (id={i})"
        for i in CLASS_NAMES
        if i not in class_counts
    ]
    if missing:
        print(f"\n[WARN] Classes defined in CLASS_NAMES but NOT in dataset:")
        for m in missing:
            print(m)
        print("       These classes will always be predicted as 'unknown'.")
        print("       Add training data for them or remove from CLASS_NAMES.")

    if imbalance > 3.0:
        print(f"\n[WARN] Imbalance ratio {imbalance:.1f}x is high.")
        print("       Use class_weight='balanced' in classifier (already set).")
        print("       Consider augmenting or collecting more data for low classes.")

    if empty_files:
        print(f"\n[WARN] {len(empty_files)} empty label files found.")
        print("       These are frames with no detected person — safe to delete.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    audit()
