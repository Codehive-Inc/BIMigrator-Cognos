import io
import zipfile
from pathlib import Path


def zip_directory(path: Path):
    buffer = io.BytesIO()
    files = path.rglob('*')
    with zipfile.ZipFile(
            buffer, 'w',
            compression=zipfile.ZIP_LZMA,
            allowZip64=True
    ) as zipped:
        for file in files:
            zipped.write(file, arcname=file.relative_to(path.parent))
    return buffer
