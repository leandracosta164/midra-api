"""Private local storage for MIDRA Engineering project documents."""
from __future__ import annotations
import base64, binascii, hashlib, re
from pathlib import Path

from app.core.settings import settings

SAFE_EXTENSIONS={
    ".pdf",".doc",".docx",".xls",".xlsx",".csv",".txt",".rtf",
    ".dwg",".dxf",".zip",".jpg",".jpeg",".png",".tif",".tiff"
}

def _root() -> Path:
    root=Path(settings.MIDRA_ENGINEERING_FILE_ROOT)
    if not root.is_absolute():
        root=Path.cwd()/root
    root.mkdir(parents=True,exist_ok=True)
    return root.resolve()

def safe_filename(name: str) -> str:
    value=Path(name).name.strip()
    value=re.sub(r"[^A-Za-z0-9._() -]+","_",value)
    if not value or value in {".",".."}:
        raise ValueError("invalid filename")
    ext=Path(value).suffix.lower()
    if ext not in SAFE_EXTENSIONS:
        raise ValueError(f"unsupported file type: {ext or 'no extension'}")
    return value[:255]

def decode_content(encoded: str) -> bytes:
    try:
        data=base64.b64decode(encoded,validate=True)
    except (binascii.Error,ValueError) as exc:
        raise ValueError("invalid base64 file content") from exc
    maximum=settings.MIDRA_ENGINEERING_MAX_FILE_MB*1024*1024
    if len(data)>maximum:
        raise ValueError(f"file exceeds {settings.MIDRA_ENGINEERING_MAX_FILE_MB} MB limit")
    if not data:
        raise ValueError("empty file")
    return data

def store(*,job_number: str,document_id: str,revision: int,
          filename: str,content: bytes) -> tuple[str,str]:
    name=safe_filename(filename)
    folder=_root()/re.sub(r"[^A-Za-z0-9._-]+","_",job_number)/document_id
    folder.mkdir(parents=True,exist_ok=True)
    stored=f"r{revision:03d}_{name}"
    path=(folder/stored).resolve()
    if _root() not in path.parents:
        raise ValueError("unsafe document path")
    path.write_bytes(content)
    return str(path.relative_to(_root())),hashlib.sha256(content).hexdigest()

def resolve(relative_path: str) -> Path:
    path=(_root()/relative_path).resolve()
    if _root() not in path.parents or not path.is_file():
        raise FileNotFoundError(relative_path)
    return path
