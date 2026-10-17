import hashlib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "scikit-learn/adult-census-income"
REVISION = "fbeef6ec0e6fd88a5028b94683144000a6b380d5"
URL = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/adult.csv"
OUT = ROOT / "data/raw/adult.csv"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(URL, OUT)
    md5 = hashlib.md5(OUT.read_bytes()).hexdigest()
    print(f"saved {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes, md5={md5})")


if __name__ == "__main__":
    main()
