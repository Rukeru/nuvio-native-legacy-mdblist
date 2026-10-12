"""Provision only the official toolchains required by this regression shard."""
from pathlib import Path
import fnmatch,hashlib,os,re,shutil,subprocess,sys,tarfile
from full_regression import partition
from resilience import fetch
from update_guard import network_command

KOTLIN=[
 ('org.jetbrains.kotlin','kotlin-stdlib','2.0.21','f31cc53f105a7e48c093683bbd5437561d1233920513774b470805641bedbc09'),
 ('org.jetbrains.kotlin','kotlin-compiler-embeddable','2.0.21','9fa8cdd1de0dccffe154c997d423ec6b5f53cd6d9177e3a77a9b0de03fb1bc81'),
 ('org.jetbrains.kotlin','kotlin-script-runtime','2.0.21','9c111f8d08ade455566272d561921adc2b2cb6b7a4ccee38d9829c5e3a1ca6a3'),
 ('org.jetbrains.kotlin','kotlin-daemon-embeddable','2.0.21','b1a0a73c5022f8dd05a638c6b76b2bd7361818a1f3860ff2644133b1dd2bdb03'),
 ('org.jetbrains.intellij.deps','trove4j','1.0.20200330','c5fd725bffab51846bf3c77db1383c60aaaebfe1b7fe2f00d23fe1b7df0a439d'),
 ('org.jetbrains.kotlinx','kotlinx-coroutines-core-jvm','1.6.4','c24c8bb27bb320c4a93871501a7e5e0c61607638907b197aef675513d4c820be'),
 ('org.jetbrains','annotations','13.0','ace2a10dc8e2d5fd34925ecac03e4988b2c0f851650c94b8cef49ba1bd111478')]

def requires_emsdk(script):
    # Conservative discovery also covers quoted SDK executable paths, not just
    # bare emcc invocations or one particular assignment style.
    return bool(re.search(r'\b(?:EMSDK_DIR|EMCC|emcc)\b',script))

def provision(root,index,count,*,selected=None):
    root=Path(root).resolve();files=[p.relative_to(root).as_posix() for p in (root/'tests').glob('*.sh')]
    selected=partition(files,index,count) if selected is None else selected
    if not set(selected)<=set(files):raise ValueError('Unknown regression fixture')
    excluded=re.search(r'case "\$n" in\s*(.*?)\) pulados=',(root/'tools/testa-tudo.sh').read_text(),re.S)
    if not excluded:raise ValueError('Upstream exclusion contract changed; inspect regression tool requirements')
    patterns=excluded.group(1).strip().split('|')
    selected=[path for path in selected if not any(fnmatch.fnmatch(Path(path).name,p) for p in patterns)]
    print('Provisioning toolchains for',len(selected),'assigned scripts',flush=True)
    dotnet=any('.csproj' in (root/path).read_text() and re.search(r'\b(?:build|run)\b',(root/path).read_text()) for path in selected)
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf8') as output:output.write('dotnet='+str(dotnet).lower()+'\n')
    legacy='tests/tizen-globalthis.sh' in selected
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf8') as output:output.write('legacy='+str(legacy).lower()+'\n')
    if legacy:
        if sys.platform!='linux':raise ValueError('The real Node 10 legacy-engine fixture requires its assigned Linux host')
        name='node-v10.24.1-linux-x64.tar.xz'
        digest='a3b9b97c23bcdc64334be6b02422e9014f040d59dcf604563ffda48003419356'
        data=fetch('https://nodejs.org/download/release/v10.24.1/'+name)
        if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Official legacy Node engine checksum mismatch')
        prefix=Path(os.environ['RUNNER_TEMP'])/'regression-legacy-node';prefix.mkdir()
        archive=prefix/name;archive.write_bytes(data)
        with tarfile.open(archive) as contents:contents.extractall(prefix,filter='data')
        node=prefix/name.removesuffix('.tar.xz')/'bin/node'
        subprocess.run([str(node),'-e',"if(typeof globalThis!=='undefined')process.exit(1);console.log(process.version)"],check=True)
        with open(os.environ['GITHUB_ENV'],'a',encoding='utf8') as env:env.write('LEGACY_NODE='+str(node)+'\n')
    browser_fixtures=('tests/entrada_texto_wgt.sh','tests/tizen-despedida.sh','tests/cachearte-wasm.sh')
    if any(path in selected for path in browser_fixtures):
        prefix=Path(os.environ['RUNNER_TEMP'])/'regression-playwright'
        network_command(['npm','install','--prefix',str(prefix),'--no-save','--ignore-scripts','--no-audit','--no-fund','playwright@1.55.1'])
        if any(path in selected for path in ('tests/tizen-despedida.sh','tests/cachearte-wasm.sh')):
            network_command([str(prefix/'node_modules/.bin/playwright'),'install','chromium'])
        with open(os.environ['GITHUB_ENV'],'a',encoding='utf8') as env:env.write('NODE_PATH='+str(prefix/'node_modules')+'\n')
    if any(path in selected for path in ('tests/android_superficie_solta.sh','tests/tombstone.sh')):
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
        if 'tests/tombstone.sh' in selected:
            network_command(['brew','install','openjdk@17'])
            prefix=Path(subprocess.check_output(['brew','--prefix','openjdk@17'],text=True).strip())
            jdk=prefix/'libexec/openjdk.jdk/Contents/Home'
            subprocess.run([str(jdk/'bin/java'),'-version'],check=True)
            with open(os.environ['GITHUB_ENV'],'a',encoding='utf8') as env:env.write('JAVA17_HOME='+str(jdk)+'\n')
    if legacy or any(requires_emsdk((root/path).read_text()) for path in selected):
        sdk=Path(os.environ['RUNNER_TEMP'])/'regression-emsdk'
        network_command(['git','clone','--depth','1','--branch','4.0.18','https://github.com/emscripten-core/emsdk',str(sdk)])
        actual=subprocess.check_output(['git','-C',str(sdk),'rev-parse','HEAD'],text=True).strip()
        if actual!='eb5eb4b3b2b792f44ded198bfe615c985da5be2c':raise ValueError('Emscripten regression SDK source checksum mismatch')
        network_command([str(sdk/'emsdk'),'install','4.0.18'])
        subprocess.run([str(sdk/'emsdk'),'activate','4.0.18'],check=True)
        with open(os.environ['GITHUB_ENV'],'a',encoding='utf8') as env:
            env.write('EMSDK_DIR='+str(sdk)+'\nEMCC='+str(sdk/'upstream/emscripten/emcc')+'\n')
        with open(os.environ['GITHUB_PATH'],'a',encoding='utf8') as paths:paths.write(str(sdk/'upstream/emscripten')+'\n')
    if any(path in selected for path in ('tests/dts_engine.sh','tests/dts_subtitles.sh')):
        # The minimal decoder under test stays source-pinned. Fixture media
        # needs the legacy full CLI encoder set, absent from current ffmpeg.
        if sys.platform=='darwin':
            network_command(['brew','install','ffmpeg@7'])
            cli=Path(subprocess.check_output(['brew','--prefix','ffmpeg@7'],text=True).strip())/'bin'
        else:
            executable=shutil.which('ffmpeg')
            if not executable:raise ValueError('Install the real FFmpeg fixture CLI before provisioning DTS')
            cli=Path(executable).parent
        encoders=subprocess.check_output([str(cli/'ffmpeg'),'-hide_banner','-encoders'],text=True,stderr=subprocess.STDOUT)
        for encoder in ('libx264','libvpx-vp9','libaom-av1','dca','aac'):
            if not re.search(r'\s'+re.escape(encoder)+r'\s',encoders):raise ValueError('Required real fixture encoder missing: '+encoder)
        os.environ['PATH']=str(cli)+os.pathsep+os.environ['PATH']
        with open(os.environ['GITHUB_PATH'],'a',encoding='utf8') as paths:paths.write(str(cli)+'\n')
        prefix=Path(os.environ['RUNNER_TEMP'])/'regression-dts-host'
        build=Path(os.environ['RUNNER_TEMP'])/'regression-dts-build'
        os.environ.update(NUVIO_DTS_HOST='1',NUVIO_DTS_ROOT=str(prefix),NUVIO_DTS_BUILD=str(build),CC='cc')
        # The upstream script verifies its own pinned FFmpeg source archive.
        if sys.platform=='darwin':
            coreutils=subprocess.check_output(['brew','--prefix','coreutils'],text=True).strip()
            os.environ['PATH']=str(Path(coreutils)/'libexec/gnubin')+os.pathsep+os.environ['PATH']
        network_command(['bash',str(root/'tools/build-dts-ffmpeg.sh')])
        with open(os.environ['GITHUB_ENV'],'a',encoding='utf8') as env:env.write('NUVIO_DTS_ROOT='+str(prefix)+'\n')
    if any(path in selected for path in ('tests/dts_pipeline.sh','tests/dts_sonda_cache.sh','tests/dts_sonda_repetida.sh','tests/p2pmotor_real.sh')):
        # The tests deliberately exercise BOTH libstdc++ string ABIs. Apple's
        # default clang/libc++ ignores the _GLIBCXX_USE_CXX11_ABI switch.
        network_command(['brew','install','gcc'])
        prefix=Path(subprocess.check_output(['brew','--prefix','gcc'],text=True).strip())
        compilers=sorted((prefix/'bin').glob('g++-*'))
        if not compilers:raise ValueError('GNU C++ compiler required by real dual-ABI fixture')
        compiler=compilers[-1]
        subprocess.run([str(compiler),'--version'],check=True)
        os.environ['CXX']=str(compiler)
        with open(os.environ['GITHUB_ENV'],'a',encoding='utf8') as env:env.write('CXX='+str(compiler)+'\n')
    if 'tests/p2pmotor_real.sh' in selected:
        prefix=Path(os.environ['RUNNER_TEMP'])/'regression-real-engine'
        subprocess.run([os.environ['CXX'],'-std=c++20','-x','c++','-','-fsyntax-only'],
                       input='#include <thread>\n#include <stop_token>\n'
                             'static_assert(__cpp_lib_jthread >= 201911L);\n'
                             'int main(){std::jthread worker([](std::stop_token){});}\n',
                       text=True,check=True)
        network_command(['brew','install','cmake'])
        network_command(['bash',str(root/'tools/p2p-motor/build-mac.sh'),str(prefix)])
        engine=prefix/'nuvio-engine'
        commit=subprocess.check_output(['git','-C',str(engine),'rev-parse','HEAD'],text=True).strip()
        if not commit.startswith('02938d7'):raise ValueError('Real engine fixture source does not match the upstream pin')
        if not (engine/'build/mac/libnuvio_engine.a').is_file():raise ValueError('Real P2P engine fixture library missing')
        print('Real P2P fixture engine source:',commit,flush=True)
        with open(os.environ['GITHUB_ENV'],'a',encoding='utf8') as env:env.write('NV_ENGINE='+str(engine)+'\n')
    if 'tests/gifbanco-tizen.sh' in selected:
        network_command(['git','-C',str(root),'fetch','origin','refs/tags/v1.4.6:refs/tags/v1.4.6'])
    if any(path in selected for path in ('tests/gifbanco-tizen.sh','tests/entrada_texto_wgt.sh')):
        chrome=Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        if not chrome.exists():network_command(['brew','install','--cask','google-chrome'])
        subprocess.run([str(chrome),'--version'],check=True)

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: regression_dependencies.py ROOT INDEX COUNT')
    provision(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]))
