"""Repack reviewed public integration sources after updating manifest digests."""
from pathlib import Path
import hashlib,zipfile
root=Path(__file__).resolve().parents[1]
with zipfile.ZipFile(root/'build-inputs/integration-bundle.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted((root/'integration').rglob('*')):
        if p.is_file():z.write(p,p.relative_to(root/'integration').as_posix())
(root/'build-inputs/integration-bundle.sha256').write_text(hashlib.sha256((root/'build-inputs/integration-bundle.zip').read_bytes()).hexdigest()+'\n',encoding='utf8',newline='\n')
print('Public integration bundle packed and checksum recorded')
