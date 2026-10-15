"""Build the actual x86_64 package required by the upstream artifact test."""
from pathlib import Path
import os,sys,subprocess,tempfile
from resilience import fetch
from update_guard import network_command


def sdk_recipe(text):
    """Recover archive CDN misses without changing packages or apt verification."""
    install=('apt-get -q install -y --no-install-recommends \\\n'
             '      gcc g++ make pkg-config file libgles2-mesa-dev libegl1-mesa-dev zlib1g-dev \\\n'
             '      ca-certificates')
    if text.count(install)!=1 or text.count('FROM --platform=linux/amd64 debian:buster-slim')!=1:
        raise ValueError('Emulator SDK recipe changed; review the archive recovery adapter')
    bounded=('( attempt=1; while ! '+install+'; do \\\n'
             '      [ "$attempt" -lt 3 ] || exit 1; attempt=$((attempt + 1)); sleep 5; \\\n'
             '    done )')
    return text.replace(install,bounded)


def prepare_sdk(root):
    if subprocess.run(['docker','image','inspect','nuvio-tpk-sdk-x64'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:return
    body=sdk_recipe((root/'tools/tpk/Dockerfile.x64').read_text())
    with tempfile.TemporaryDirectory(prefix='nuvio-emulator-sdk-') as folder:
        generated=Path(folder)/'Dockerfile';generated.write_text(body)
        subprocess.run(['docker','build','--platform','linux/amd64','-f',str(generated),'-t','nuvio-tpk-sdk-x64',str(root/'tools/tpk')],check=True)


def prepare(root):
    root=Path(root).resolve()
    if sys.platform!='linux':raise ValueError('Emulator package requires native Linux Docker')
    if not os.environ.get('NUVIO_PROPERTIES'):raise ValueError('Shared build configuration is required')
    subprocess.run(['docker','info'],check=True,stdout=subprocess.DEVNULL)
    sdk=os.environ['DOTNET_ROOT']
    installer=Path(os.environ['RUNNER_TEMP'])/'regression-tizen-workload.sh'
    installer.write_bytes(fetch('https://raw.githubusercontent.com/Samsung/Tizen.NET/6ab8cb41e7ccab90a3ba838e7f6d6b38a9c4ec08/workload/scripts/workload-install.sh'))
    network_command(['bash',str(installer),'-v','10.0.120','-t','8.0.400','-d',sdk])
    prepare_sdk(root)
    env={**os.environ,'NUVIO_TPK_ARCH':'x86_64','NUVIO_P2P_MOTOR':'none','NUVIO_BUILD_JOBS':'4'}
    subprocess.run(['bash','tools/tpk.sh'],cwd=root,env=env,check=True)
    # The original fixture checks ELF architecture, source/core equality,
    # current host files, manifest and absence of the ARM engine. Never fake it.
    subprocess.run(['bash','tests/tpk_x64.sh'],cwd=root,env=env,check=True)

if __name__=='__main__':prepare(sys.argv[1])
