"""Nonpublishing paired audit; every original C assertion remains active."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main(reference, candidate, output):
    output.mkdir(parents=True, exist_ok=True)
    paths = ['tests/streamfit_redirect_range.c', 'tests/streamfit_redirect_range.sh',
             'tests/streamfit_diagnostico_server.py', 'src/streamfitdiag.c',
             'src/streamfitdiag.h', 'src/streamfit.c', 'src/streamfit.h',
             'src/redemarca.c', 'src/redemarca.h', 'src/vazao.c', 'src/vazao.h',
             'src/rede.c', 'src/rede.h', 'src/redeurl.c', 'src/rede_pedido.inc']
    hashes = {}
    for name in paths:
        a, b = (reference / name).read_bytes(), (candidate / name).read_bytes()
        hashes[name] = {'reference': hashlib.sha256(a).hexdigest(),
                        'candidate': hashlib.sha256(b).hexdigest()}
    (output / 'source-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    if any(x['reference'] != x['candidate'] for x in hashes.values()):
        raise RuntimeError('Audit inputs differ: inspect source-hashes.json before classifying')
    results = []
    for mode in ['original', 'nodelay', 'paced']:
        for repeat in range(1, 4):
            for label, root in [('reference', reference), ('candidate', candidate)]:
                server = root / 'tests/streamfit_diagnostico_server.py'
                original = server.read_text()
                modified = original
                if mode == 'nodelay':
                    modified = modified.replace('import sys\n', 'import sys\nimport socket\n')
                    modified = modified.replace('    def log_message(self, *args):',
                        '    def setup(self):\n        super().setup()\n'
                        '        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)\n\n'
                        '    def log_message(self, *args):')
                if mode == 'paced':
                    modified = modified.replace('        try:\n            for i in range(200):',
                        '        deadline = time.monotonic()\n        try:\n            for i in range(200):')
                    modified = modified.replace('                    time.sleep(.1)',
                        '                    deadline += .1\n'
                        '                    time.sleep(max(0, deadline - time.monotonic()))')
                # Observe actual sleeps without changing requested delays. No URLs/headers.
                trace = '''
import threading
_sleep = time.sleep
_state = threading.local()
def measured_sleep(delay):
    before = time.monotonic()
    _sleep(delay)
    elapsed = time.monotonic() - before
    _state.count = getattr(_state, 'count', 0) + 1
    _state.requested = getattr(_state, 'requested', 0) + delay
    _state.actual = getattr(_state, 'actual', 0) + elapsed
    if _state.count % 10 == 0:
        print('server_sleep', threading.current_thread().name, _state.count,
              round(_state.requested, 6), round(_state.actual, 6), flush=True)
time.sleep = measured_sleep
'''
                modified = modified.replace('class Handler(', trace + '\nclass Handler(')
                env = dict(os.environ, PYTHONPATH=str(root / 'tests/stubs/host'))
                try:
                    server.write_text(modified)
                    run = subprocess.run(['bash', 'tests/streamfit_redirect_range.sh'], cwd=root,
                                         env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, timeout=90)
                    name = f'{mode}-{repeat}-{label}.log'
                    (output / name).write_text(run.stdout)
                    result = {'mode': mode, 'repeat': repeat, 'source': label,
                              'exit_code': run.returncode, 'log': name}
                    results.append(result)
                    print(json.dumps(result), flush=True)
                finally:
                    server.write_text(original)
                (output / 'results.json').write_text(json.dumps({
                    'diagnostic_only': True, 'builder': os.environ['GITHUB_SHA'],
                    'results': results}, indent=2) + '\n')


if __name__ == '__main__':
    main(*(Path(x).resolve() for x in sys.argv[1:]))
