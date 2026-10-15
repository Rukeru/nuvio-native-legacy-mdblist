"""Resolve reviewed engine pins and the upstream API overlay without executing shell."""
from pathlib import Path
import hashlib,re,subprocess


def pin_recipe(root, recipe):
    root=Path(root); recipe=Path(recipe)
    body=recipe.read_text(encoding='utf8')
    pins=re.findall(r'^COMMIT=([0-9a-f]{6,40})$',body,re.M)
    if len(pins)==1:return recipe,'COMMIT',pins[0],None
    if pins:raise ValueError('Ambiguous engine commit pin')
    if '. tools/p2p-motor/pasta.sh;' not in body or 'nv_p2p_fonte "$W/nuvio-engine"' not in body:
        raise ValueError('Unrecognized engine source recipe')
    shared=root/'tools/p2p-motor/pasta.sh'
    text=shared.read_text(encoding='utf8')
    pins=re.findall(r'^NV_P2P_COMMIT=([0-9a-f]{7,40})$',text,re.M)
    if len(pins)!=1 or 'checkout -q "$NV_P2P_COMMIT"' not in text:
        raise ValueError('Missing unique immutable shared engine pin')
    overlay=root/'tools/p2p-motor/janela-334.patch'
    if 'git -C "$1" apply "$p"' not in text or 'janela-334.patch' not in text or not overlay.is_file():
        raise ValueError('Unrecognized engine overlay recipe')
    return shared,'NV_P2P_COMMIT',pins[0],overlay


def record_overlay(state, overlay):
    if overlay:
        state['engine_overlay']={'path':'tools/p2p-motor/janela-334.patch',
                                 'sha256':hashlib.sha256(overlay.read_bytes()).hexdigest()}


def apply_header_overlay(engine_root, overlay):
    if not overlay:return
    # Apply only the reviewed public header; the official TPK already contains
    # the matching patched engine. Reject any stale context or malformed patch.
    engine_root=Path(engine_root).resolve()
    target=(engine_root/'include/nuvio_engine/nuvio_engine.h').as_posix()
    command=['git','apply','--no-index','--unsafe-paths',
             '--directory='+engine_root.as_posix(),'--include='+target]
    subprocess.run(command+['--check',str(overlay.resolve())],cwd=engine_root.anchor,check=True)
    subprocess.run(command+[str(overlay.resolve())],cwd=engine_root.anchor,check=True)
    header=Path(engine_root)/'include/nuvio_engine/nuvio_engine.h'
    if '#define NUVIO_ENGINE_API_VERSION 4U' not in header.read_text(encoding='utf8'):
        raise ValueError('Reviewed engine overlay did not provide API 4')
