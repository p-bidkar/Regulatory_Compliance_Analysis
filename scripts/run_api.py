import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import uvicorn


def main() -> None:
    uvicorn.run("regcomply.api.app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
