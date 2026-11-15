from pathlib import Path
import struct
import zlib

import numpy as np


DATA_DIR = Path(r"C:\Users\XOCEA\eter-ml-data")

INPUT_FILE = DATA_DIR / "eter_cnn_demo.example.npz"
OUTPUT_DIR = DATA_DIR / "imagenes"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def png_chunk(tag: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + tag
        + payload
        + struct.pack(
            ">I",
            zlib.crc32(tag + payload) & 0xFFFFFFFF,
        )
    )


def save_png(path: Path, rgb: np.ndarray) -> None:
    """Guardar una imagen RGB como PNG sin Pillow."""

    height, width, channels = rgb.shape

    if channels != 3 or rgb.dtype != np.uint8:
        raise ValueError("Se necesita una imagen RGB uint8.")

    raw = b"".join(
        b"\x00" + rgb[row].tobytes()
        for row in range(height)
    )

    header = struct.pack(
        ">IIBBBBB",
        width,
        height,
        8,  # Bits por canal
        2,  # RGB
        0,
        0,
        0,
    )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(raw, 6))
        + png_chunk(b"IEND", b"")
    )

    path.write_bytes(png)


def grayscale(image: np.ndarray) -> np.ndarray:
    """Mostrar estrellas y estructuras en escala de grises."""

    low, high = np.percentile(image, [1, 99.5])

    normalized = np.clip(
        (image - low) / max(high - low, 1e-6),
        0,
        1,
    )

    gray = (normalized * 255).astype(np.uint8)

    return np.repeat(
        gray[:, :, np.newaxis],
        3,
        axis=2,
    )


def difference_rgb(image: np.ndarray) -> np.ndarray:
    """
    Mostrar diferencias:
    rojo = aumento
    azul = disminucion
    negro = sin cambio significativo visual
    """

    scale = max(
        float(np.percentile(np.abs(image), 99.5)),
        1e-6,
    )

    normalized = np.clip(image / scale, -1, 1)

    rgb = np.zeros(
        (*image.shape, 3),
        dtype=np.uint8,
    )

    rgb[:, :, 0] = (
        np.clip(normalized, 0, 1) * 255
    ).astype(np.uint8)

    rgb[:, :, 2] = (
        np.clip(-normalized, 0, 1) * 255
    ).astype(np.uint8)

    return rgb


def enlarge(image: np.ndarray, factor: int = 5) -> np.ndarray:
    """Aumentar tamaño para observar los pixeles."""

    return np.repeat(
        np.repeat(image, factor, axis=0),
        factor,
        axis=1,
    )


def main() -> None:
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(INPUT_FILE)

    with np.load(INPUT_FILE, allow_pickle=False) as data:
        science = data["science"]
        reference = data["reference"]
        difference = data["difference"]

    for image in (science, reference, difference):
        if image.shape != (63, 63):
            raise ValueError(
                f"Forma incorrecta: {image.shape}"
            )

    images = {
        "01_science.png": grayscale(science),
        "02_reference.png": grayscale(reference),
        "03_difference.png": difference_rgb(difference),
    }

    for filename, image in images.items():
        save_png(
            OUTPUT_DIR / filename,
            enlarge(image),
        )

    separator = np.full(
        (63, 8, 3),
        255,
        dtype=np.uint8,
    )

    comparison = np.concatenate(
        [
            images["01_science.png"],
            separator,
            images["02_reference.png"],
            separator,
            images["03_difference.png"],
        ],
        axis=1,
    )

    save_png(
        OUTPUT_DIR / "04_comparacion.png",
        enlarge(comparison),
    )

    print("Imagenes generadas correctamente:")
    for path in sorted(OUTPUT_DIR.glob("*.png")):
        print(path)


if __name__ == "__main__":
    main()
