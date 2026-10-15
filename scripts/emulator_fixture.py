"""Build the actual x86_64 package required by the upstream artifact test."""
from pathlib import Path
import os,sys,subprocess
from resilience import fetch
from update_guard import network_command


def prepare(root):
    root=Path(root).resolve()
    if sys.platform!='linux':raise ValueError('Emulator package requires native Linux Docker')
    if not os.environ.get('NUVIO_PROPERTIES'):raise ValueError('Shared build configuration is required')
    subprocess.run(['docker','info'],check=True,stdout=subprocess.DEVNULL)
    sdk=os.environ['DOTNET_ROOT']
    installer=Path(os.environ['RUNNER_TEMP'])/'regression-tizen-workload.sh'
    installer.write_bytes(fetch('https://raw.githubusercontent.com/Samsung/Tizen.NET/6ab8cb41e7ccab90a3ba838e7f6d6b38a9c4ec08/workload/scripts/workload-install.sh'))
    network_command(['bash',str(installer),'-v','10.0.120','-t','8.0.400','-d',sdk])
    env={**os.environ,'NUVIO_TPK_ARCH':'x86_64','NUVIO_P2P_MOTOR':'none','NUVIO_BUILD_JOBS':'4'}
    subprocess.run(['bash','tools/tpk.sh'],cwd=root,env=env,check=True)
    # The original fixture checks ELF architecture, source/core equality,
    # current host files, manifest and absence of the ARM engine. Never fake it.
    subprocess.run(['bash','tests/tpk_x64.sh'],cwd=root,env=env,check=True)

if __name__=='__main__':prepare(sys.argv[1])
