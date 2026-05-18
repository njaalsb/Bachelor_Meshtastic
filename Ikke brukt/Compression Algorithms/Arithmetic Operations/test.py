import os
from pathlib import Path
import cv2

# --- INPUT ---
in_path = Path(__file__).parent / "My mom is kinda homeless.jpg"
img = cv2.imread(str(in_path), cv2.IMREAD_UNCHANGED)
out_dir = Path(Path(__file__).parent / "compressed_out")
out_dir.mkdir(exist_ok=True)

def human_bytes(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

# Les originalfilstørrelse
if not in_path.exists():
    raise FileNotFoundError(f"Fant ikke filen: {in_path.resolve()}")

orig_size = in_path.stat().st_size

# Les bildet med OpenCV (støtter PNG m/alpha)
img = cv2.imread(str(in_path), cv2.IMREAD_UNCHANGED)
if img is None:
    raise RuntimeError("cv2.imread feilet. Sjekk filnavn og at bildet faktisk kan åpnes.")

print(f"Original: {in_path.name}  |  {human_bytes(orig_size)}")

# Hvis bildet har alpha (RGBA), konverter til BGR for JPEG (JPEG støtter ikke alpha)
has_alpha = (len(img.shape) == 3 and img.shape[2] == 4)
if has_alpha:
    bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
else:
    bgr = img

# --- Test JPEG kvaliteter ---
print("\nJPEG:")
for q in [95, 90, 85, 80, 70, 60, 50, 40, 30, 20, 10]:
    out_path = out_dir / f"{in_path.stem}_q{q}.jpg"
    ok = cv2.imwrite(str(out_path), bgr, [cv2.IMWRITE_JPEG_QUALITY, q])
    if not ok:
        print(f"  q={q}: klarte ikke å skrive fil.")
        continue
    new_size = out_path.stat().st_size
    ratio = orig_size / new_size if new_size else float("inf")
    print(f"  q={q:>2}: {human_bytes(new_size):>9}  |  {ratio:>6.2f}x mindre")

# --- Test WebP kvaliteter (ofte mye bedre enn JPEG) ---
print("\nWebP:")
for q in [100, 90, 80, 70, 60, 50, 40, 30, 20, 10]:
    out_path = out_dir / f"{in_path.stem}_q{q}.webp"
    ok = cv2.imwrite(str(out_path), img, [cv2.IMWRITE_WEBP_QUALITY, q])
    if not ok:
        print(f"  q={q}: klarte ikke å skrive fil.")
        continue
    new_size = out_path.stat().st_size
    ratio = orig_size / new_size if new_size else float("inf")
    print(f"  q={q:>3}: {human_bytes(new_size):>9}  |  {ratio:>6.2f}x mindre")

print(f"\nFerdig. Filer ligger i: {out_dir.resolve()}")
