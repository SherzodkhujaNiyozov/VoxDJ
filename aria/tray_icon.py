"""Tray ikonkasini PIL bilan chizadi (tashqi rasm fayli kerak emas)."""

from PIL import Image, ImageDraw


def make_icon(active: bool = True) -> Image.Image:
    """Mikrofon ko'rinishidagi oddiy ikonka. active=False bo'lsa kulrang."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    accent = (37, 99, 235, 255) if active else (120, 120, 120, 255)
    # Mikrofon tanasi
    d.rounded_rectangle([26, 12, 38, 38], radius=6, fill=accent)
    # Mikrofon ushlagichi (yarim doira)
    d.arc([20, 22, 44, 46], start=0, end=180, fill=accent, width=4)
    # Oyoq
    d.line([32, 46, 32, 54], fill=accent, width=4)
    d.line([24, 54, 40, 54], fill=accent, width=4)
    return img
