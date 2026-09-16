from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    size = 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, size - 8, size - 8), fill=(61, 214, 208, 255))
    draw.ellipse((28, 28, size - 28, size - 28), fill=(11, 18, 32, 255))
    try:
        font = ImageFont.truetype("arialbd.ttf", 140)
    except OSError:
        font = ImageFont.load_default()
    text = "J"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - 12), text, fill=(61, 214, 208, 255), font=font)
    ico_path = assets / "jarvis.ico"
    png_path = assets / "jarvis.png"
    image.save(png_path)
    image.save(ico_path, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Icona creata: {ico_path}")


if __name__ == "__main__":
    main()
