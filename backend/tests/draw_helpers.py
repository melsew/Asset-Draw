import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
VECTORS_PATH = ROOT / "tests" / "vectors" / "draw_v1.json"


def load_vectors() -> dict:
    return json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
