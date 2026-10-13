"""Opt-in host compiler accelerator. Unknown driver forms pass through unchanged.

Only ordinary C compile-and-link commands are split into independent translation
units, as the compiler driver normally does. Every fixture is still linked and
executed. ccache validates compiler, flags, sources and included headers; no
sloppiness, result caching, source edits or test-result reuse is permitted.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json, os, re, shutil, subprocess, sys, tempfile, time


def plan(args, directory):
    sources=[]; compile_flags=[]; link=[]; output=None; i=0
    # Deliberately narrow grammar. LTO, response files, side outputs, mixed
    # languages, per-file language switches and driver introspection fall back.
    pairs={'-I','-D','-U','-isystem','-iquote','-include','-isysroot'}
    singles={'-g','-g0','-g1','-g2','-g3','-pthread','-pipe','-pedantic',
             '-pedantic-errors','-ansi','-fPIC','-fpic','-fno-common','-fcommon',
             '-fno-omit-frame-pointer','-fno-strict-aliasing'}
    while i<len(args):
        arg=args[i]
        if arg=='-o':
            if output is not None or i+1==len(args):return None
            output=args[i+1]
            if output=='-':return None
            link.extend(args[i:i+2]);i+=2;continue
        if arg in pairs:
            if i+1==len(args):return None
            compile_flags.extend(args[i:i+2]);link.extend(args[i:i+2]);i+=2;continue
        if arg in ('-L','-l','-framework'):
            if i+1==len(args):return None
            link.extend(args[i:i+2]);i+=2;continue
        if arg.startswith(('-l','-L','-Wl,')):
            link.append(arg);i+=1;continue
        if arg in singles or re.fullmatch(r'-O(?:[0123sg]|fast)',arg) or re.fullmatch(r'-std=(?:c|gnu)\d+',arg) or arg.startswith(('-I','-D','-U','-Wno-','-Werror','-Wall','-Wextra')):
            compile_flags.append(arg);link.append(arg);i+=1;continue
        if not arg.startswith('-') and arg.endswith('.c'):
            obj=str(Path(directory)/('unit-%04d.o'%len(sources)))
            sources.append((arg,obj));link.append(obj);i+=1;continue
        if not arg.startswith('-') and arg.endswith(('.o','.a','.so','.dylib')):
            link.append(arg);i+=1;continue
        return None
    if not output or len(sources)<2:return None
    return [(compile_flags+[source,'-c','-o',obj]) for source,obj in sources],link


def execute(args):
    compiler=os.environ['NV_REAL_CC'];started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='nuvio-ci-objects-') as directory:
        commands=plan(args,directory)
        if commands is None:return subprocess.call([compiler,*args])
        cache=shutil.which('ccache')
        if not cache:raise RuntimeError('Opt-in compiler cache requested but ccache is unavailable')
        env=cache_environment()
        # Two compilation processes at most; never parallelize timed tests or
        # contend with benchmark rendering in this process.
        workers=min(2,os.cpu_count() or 1)
        def compile_one(command):
            return subprocess.run([cache,compiler,*command],env=env,
                                  stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results=list(pool.map(compile_one,commands[0]))
        for result in results:sys.stdout.buffer.write(result.stdout)
        sys.stdout.buffer.flush()
        failed=next((r.returncode for r in results if r.returncode),0)
        if failed:return failed
        result=subprocess.call([compiler,*commands[1]])
        timing=os.environ.get('NV_COMPILE_TIMINGS')
        if timing:
            # No compiler command lines: those can contain application keys.
            with open(timing,'a',encoding='utf8') as f:
                f.write(json.dumps({'units':len(commands[0]),'seconds':time.monotonic()-started,
                                    'exit_code':result})+'\n')
        return result


def install(directory):
    compiler=shutil.which('cc')
    if not compiler:raise RuntimeError('A real native compiler is required')
    # Validate cache configuration before starting any expensive fixture.
    subprocess.run(['ccache','--show-config'],env=cache_environment(),check=True,
                   stdout=subprocess.DEVNULL)
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    wrapper=directory/'cc'
    if Path(compiler).resolve()==wrapper:raise RuntimeError('Recursive compiler wrapper')
    import shlex
    wrapper.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+
                       shlex.quote(str(Path(__file__).resolve()))+' "$@"\n')
    wrapper.chmod(0o755)
    with open(os.environ['GITHUB_ENV'],'a') as f:f.write('NV_REAL_CC='+compiler+'\n')
    with open(os.environ['GITHUB_PATH'],'a') as f:f.write(str(directory)+'\n')


def cache_environment():
    env={**os.environ,'CCACHE_COMPILERCHECK':'content','CCACHE_SLOPPINESS':'',
         'CCACHE_NODIRECT':'1'}
    # ccache boolean environment variables use NO-prefixed names to disable;
    # setting CCACHE_DIRECT=false is a configuration error, not false.
    env.pop('CCACHE_DIRECT',None)
    return env


if __name__=='__main__':
    if sys.argv[1:2]==['install']:install(sys.argv[2])
    else:sys.exit(execute(sys.argv[1:]))
