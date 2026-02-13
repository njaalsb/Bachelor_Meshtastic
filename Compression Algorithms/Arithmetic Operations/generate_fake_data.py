import numpy as np
from pathlib import Path

W = 160
H = 120

def generate_fake_frame():
    """
    Lager et 160x120 16-bit 'temperaturbilde'
    med gradient + støy + varm flekk.
    """
    y = np.linspace(0, 1, H).reshape(H, 1)
    x = np.linspace(0, 1, W).reshape(1, W)

    # grunn-gradient
    base = 12000 + 4000 * x + 3000 * y

    # varm flekk i midten
    cx, cy = 0.5, 0.5
    dist = np.sqrt((x - cx)**2 + (y - cy)**2)
    hotspot = np.exp(-(dist**2) / 0.02) * 8000

    # litt støy
    noise = np.random.normal(0, 200, (H, W))

    frame = base + hotspot + noise
    frame = np.clip(frame, 0, 65535)

    return frame.astype(np.uint16)

def write_vospi_txt(frame, out_path: Path):
    """
    Lager 240 VOSPI PACKET blocks.
    Hver pakke inneholder 80 pixels (160 bytes).
    """
    with out_path.open("w", encoding="utf-8") as f:
        for row in range(H):
            # Lepton 3.x: 2 packets per row
            for half in range(2):
                f.write("===================VOSPI PACKET===========================\n")

                # Fake header (første to bytes brukes ofte til row id)
                header0 = (row >> 8) & 0xFF
                header1 = row & 0xFF
                f.write(f"{header0} {header1} 250 116\n")

                start = half * 80
                end = start + 80
                row_pixels = frame[row, start:end]

                # skriv 80 pixels som (hi lo hi lo ...)
                for px in row_pixels:
                    hi = (px >> 8) & 0xFF
                    lo = px & 0xFF
                    f.write(f"{hi} {lo} ")

                f.write("\nEND OF VOSPI PACKET\n")
                f.write("Kom ut av sync loop\n")

    print(f"Testdata skrevet til: {out_path.resolve()}")

if __name__ == "__main__":
    base = Path(__file__).parent
    out = base / "ir_sensor_image.txt"

    frame = generate_fake_frame()
    write_vospi_txt(frame, out)
