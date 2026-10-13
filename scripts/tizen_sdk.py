"""Build the upstream SDK using its exact ARMv5 base from Google's cache.

Generate a separate Dockerfile; retain the upstream recipe unchanged. A changed
base/architecture requires review, rather than silently selecting a newer ABI.
"""
from pathlib import Path
import re, subprocess, tempfile

BASE='FROM --platform=linux/arm/v5 arm32v5/debian:buster-slim'
MIRROR='mirror.gcr.io/arm32v5/debian@sha256:0f7c9f2e2249c0a1b9fb50213e497d75d86a83070a38eb558dfc6e3c1084663a'

def dockerfile(text):
    lines=re.findall(r'^FROM[^\r\n]*',text,re.M)
    if lines!=[BASE]:
        raise ValueError('Tizen SDK base or architecture changed; adapt the reviewed tizen-sdk adapter')
    return text.replace(BASE,'FROM --platform=linux/arm/v5 '+MIRROR)

def check(source):
    return dockerfile((Path(source)/'tools/tpk/Dockerfile').read_text())

def build(source='upstream'):
    body=check(source)
    if subprocess.run(['docker','image','inspect','nuvio-tpk-sdk'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:return
    with tempfile.TemporaryDirectory(prefix='nuvio-tpk-sdk-') as folder:
        generated=Path(folder)/'Dockerfile';generated.write_text(body)
        subprocess.run(['docker','build','--platform','linux/arm/v5','-t','nuvio-tpk-sdk','-f',str(generated),str(Path(source)/'tools/tpk')],check=True)

if __name__=='__main__':
    import sys
    if '--check' in sys.argv:check('upstream');print('Tizen SDK base/architecture contract passed')
    else:build()
