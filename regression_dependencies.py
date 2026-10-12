"""Provision only the official toolchains required by this regression shard."""
from pathlib import Path
import fnmatch,hashlib,os,re,subprocess,sys
from full_regression import partition
from resilience import fetch
from update_guard import network_command

KOTLIN=[
 ('org.jetbrains.kotlin','kotlin-stdlib','2.0.21','f31cc53f105a7e48c093683bbd5437561d1233920513774b470805641bedbc09'),
 ('org.jetbrains.kotlin','kotlin-compiler-embeddable','2.0.21','9fa8cdd1de0dccffe154c997d423ec6b5f53cd6d9177e3a77a9b0de03fb1bc81'),
 ('org.jetbrains.kotlin','kotlin-script-runtime','2.0.21','9c111f8d08ade455566272d561921adc2b2cb6b7a4ccee38d9829c5e3a1ca6a3'),
 ('org.jetbrains.intellij.deps','trove4j','1.0.20200330','c5fd725bffab51846bf3c77db1383c60aaaebfe1b7fe2f00d23fe1b7df0a439d'),
 ('org.jetbrains.kotlinx','kotlinx-coroutines-core-jvm','1.6.4','c24c8bb27bb320c4a93871501a7e5e0c61607638907b197aef675513d4c820be'),
 ('org.jetbrains','annotations','13.0','ace2a10dc8e2d5fd34925ecac03e4988b2c0f851650c94b8cef49ba1bd111478')]

def provision(root,index,count):
    root=Path(root).resolve();files=[p.relative_to(root).as_posix() for p in (root/'tests').glob('*.sh')]
    selected=partition(files,index,count)
    excluded=re.search(r'case "\$n" in\s*(.*?)\) pulados=',(root/'tools/testa-tudo.sh').read_text(),re.S)
    if not excluded:raise ValueError('Upstream exclusion contract changed; inspect regression tool requirements')
    patterns=excluded.group(1).strip().split('|')
    selected=[path for path in selected if not any(fnmatch.fnmatch(Path(path).name,p) for p in patterns)]
    print('Provisioning toolchains for',len(selected),'assigned scripts',flush=True)
    dotnet=any(re.search(r'\bdotnet (?:build|run)',(root/path).read_text()) for path in selected)
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf8') as output:output.write('dotnet='+str(dotnet).lower()+'\n')
    if 'tests/entrada_texto_wgt.sh' in selected:
        prefix=Path(os.environ['RUNNER_TEMP'])/'regression-playwright'
        network_command(['npm','install','--prefix',str(prefix),'--no-save','--ignore-scripts','--no-audit','--no-fund','playwright-core@1.55.1'])
        with open(os.environ['GITHUB_ENV'],'a',encoding='utf8') as env:env.write('NODE_PATH='+str(prefix/'node_modules')+'\n')
    if 'tests/android_superficie_solta.sh' in selected:
        for group,name,version,digest in KOTLIN:
            filename=name+'-'+version+'.jar'
            path=Path.home()/'.gradle/caches/modules-2/files-2.1'/group/name/version/'verified-ci'/filename
            path.parent.mkdir(parents=True,exist_ok=True)
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                url='https://repo.maven.apache.org/maven2/'+group.replace('.','/')+'/'+name+'/'+version+'/'+filename
                data=fetch(url)
                if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Kotlin regression tool checksum mismatch: '+name)
                path.write_bytes(data)
        subprocess.run(['java','-version'],check=True)
    if any(re.search(r'^(?:EMCC=|emcc |source .*EMSDK)|\bemcc\s',(root/path).read_text(),re.M) for path in selected):
        sdk=Path(os.environ['RUNNER_TEMP'])/'regression-emsdk'
        network_command(['git','clone','--depth','1','--branch','4.0.18','https://github.com/emscripten-core/emsdk',str(sdk)])
        actual=subprocess.check_output(['git','-C',str(sdk),'rev-parse','HEAD'],text=True).strip()
        if actual!='eb5eb4b3b2b792f44ded198bfe615c985da5be2c':raise ValueError('Emscripten regression SDK source checksum mismatch')
        network_command([str(sdk/'emsdk'),'install','4.0.18'])
        subprocess.run([str(sdk/'emsdk'),'activate','4.0.18'],check=True)
        with open(os.environ['GITHUB_ENV'],'a',encoding='utf8') as env:env.write('EMSDK_DIR='+str(sdk)+'\n')
        with open(os.environ['GITHUB_PATH'],'a',encoding='utf8') as paths:paths.write(str(sdk/'upstream/emscripten')+'\n')
    if any(path in selected for path in ('tests/dts_engine.sh','tests/dts_subtitles.sh')):
        prefix=Path(os.environ['RUNNER_TEMP'])/'regression-dts-host'
        build=Path(os.environ['RUNNER_TEMP'])/'regression-dts-build'
        os.environ.update(NUVIO_DTS_HOST='1',NUVIO_DTS_ROOT=str(prefix),NUVIO_DTS_BUILD=str(build),CC='cc')
        # The upstream script verifies its own pinned FFmpeg source archive.
        coreutils=subprocess.check_output(['brew','--prefix','coreutils'],text=True).strip()
        os.environ['PATH']=str(Path(coreutils)/'libexec/gnubin')+os.pathsep+os.environ['PATH']
        network_command(['bash',str(root/'tools/build-dts-ffmpeg.sh')])
        with open(os.environ['GITHUB_ENV'],'a',encoding='utf8') as env:env.write('NUVIO_DTS_ROOT='+str(prefix)+'\n')
    if any(path in selected for path in ('tests/dts_pipeline.sh','tests/dts_sonda_cache.sh','tests/dts_sonda_repetida.sh')):
        # The tests deliberately exercise BOTH libstdc++ string ABIs. Apple's
        # default clang/libc++ ignores the _GLIBCXX_USE_CXX11_ABI switch.
        network_command(['brew','install','gcc'])
        prefix=Path(subprocess.check_output(['brew','--prefix','gcc'],text=True).strip())
        compilers=sorted((prefix/'bin').glob('g++-*'))
        if not compilers:raise ValueError('GNU C++ compiler required by real dual-ABI fixture')
        compiler=compilers[-1]
        subprocess.run([str(compiler),'--version'],check=True)
        with open(os.environ['GITHUB_ENV'],'a',encoding='utf8') as env:env.write('CXX='+str(compiler)+'\n')
    if 'tests/gifbanco-tizen.sh' in selected:
        network_command(['git','-C',str(root),'fetch','origin','refs/tags/v1.4.6:refs/tags/v1.4.6'])
    if any(path in selected for path in ('tests/gifbanco-tizen.sh','tests/entrada_texto_wgt.sh')):
        chrome=Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        if not chrome.exists():network_command(['brew','install','--cask','google-chrome'])
        subprocess.run([str(chrome),'--version'],check=True)

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: regression_dependencies.py ROOT INDEX COUNT')
    provision(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]))
