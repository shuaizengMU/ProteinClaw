import json
import shutil
from pathlib import Path
from importlib.resources import files, as_file
from fastapi import APIRouter, HTTPException

router = APIRouter()

USER_CASE_STUDIES_PATH = Path("~/.config/proteinclaw/case-studies.json").expanduser()

_BUNDLED = files("proteinclaw.resources").joinpath("case-studies.json")


def _load() -> dict:
    if not USER_CASE_STUDIES_PATH.exists():
        USER_CASE_STUDIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with as_file(_BUNDLED) as bundled_path:
            shutil.copy(bundled_path, USER_CASE_STUDIES_PATH)
    try:
        return json.loads(USER_CASE_STUDIES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read case studies: {exc}")


@router.get("/api/case-studies")
async def get_case_studies():
    return _load()
