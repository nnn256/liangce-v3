"""Build the pinned user-requested TDX protocol bridge with the local Go toolchain."""
from pathlib import Path
import io,os,shutil,subprocess,tarfile
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
COMMIT='ea07dccb67aeb92ebde851ac31503b4bf457a318'


def main():
    if not shutil.which('go'):raise SystemExit('Install Go1.23+ from https://go.dev/dl/ before building the TDX bridge.')
    folder=ROOT/'.runtime/tdx-api-build';folder.mkdir(parents=True,exist_ok=True)
    with urlopen('https://codeload.github.com/oficcejo/tdx-api/tar.gz/'+COMMIT,timeout=90) as response:raw=response.read()
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        for member in archive.getmembers():
            parts=Path(member.name).parts[1:]
            if not parts or member.issym() or member.islnk():continue
            target=(folder/Path(*parts)).resolve()
            if not target.is_relative_to(folder.resolve()):raise ValueError('Unsafe source archive member')
            if member.isfile():
                source=archive.extractfile(member)
                if source:
                    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read())
    shutil.copyfile(ROOT/'services/tdxbridge/main.go',folder/'web/liangce_bridge.go')
    binary=folder/('liangce-tdx.exe' if os.name=='nt' else 'liangce-tdx')
    subprocess.run(['go','build','-trimpath','-ldflags=-s -w','-o',str(binary),'liangce_bridge.go'],cwd=folder/'web',check=True)
    print(str(binary));print('Set LIANGCE_TDX_BINARY to this path; start_local.cmd detects the Windows build automatically.')


if __name__=='__main__':main()
