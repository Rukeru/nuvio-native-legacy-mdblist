"""Identity of the installed Tizen host, resources, engine and packaging rules."""
from pathlib import Path
import hashlib
import re
import sys

ART_DIRS = 'icones icones-app badges selos marcas prov editorial logo poster ep elenco'.split()
TEXT = {'.cs', '.csproj', '.xml', '.json', '.txt', '.svg', '.pem', '.sh'}

def shell_id(source, engine):
    source = Path(source)
    files = set((source / 'tizen-tpk').glob('*.cs'))
    files.update((source / 'tizen-tpk/NuvioTpk').glob('*.csproj'))
    files.add(source / 'tizen-tpk/NuvioTpk/tizen-manifest.xml')
    for folder in ['deploy/app/fonts', 'deploy/app/licencas'] + ['deploy/app/art/' + p for p in ART_DIRS]:
        files.update(p for p in (source / folder).rglob('*') if p.is_file())
    files.update((source / 'deploy/app/art').glob('*.jpg'))
    for name in ['tizen-tpk/silencio.mp4', 'deploy/app/tizen/icon.png',
                 'deploy/app/art/discord-ca.pem', 'deploy/app/art/addons-recomendados.txt',
                 'tools/tpk.sh', 'tools/tizen-art.sh']:
        if (source / name).exists(): files.add(source / name)
    digest = hashlib.sha256(b'nuvio-mdblist-shell-v1\0')
    for p in sorted(files, key=lambda f: f.relative_to(source).as_posix()):
        data = p.read_bytes()
        if p.suffix in TEXT or p.name.startswith(('LICENSE', 'NOTICE', 'COPYING')):
            data = data.replace(b'\r\n', b'\n')
        if p.name == 'tizen-manifest.xml':
            # The package version changes without changing the shell ABI.
            data = re.sub(rb'(?<![\w-])version="[0-9.]+"', b'version="VERSION"', data)
        digest.update(p.relative_to(source).as_posix().encode() + b'\0' + hashlib.sha256(data).digest())
    digest.update(b'libnuvio_engine.so\0' + hashlib.sha256(Path(engine).read_bytes()).digest())
    return digest.hexdigest()

if __name__ == '__main__': print(shell_id(sys.argv[1], sys.argv[2]))
