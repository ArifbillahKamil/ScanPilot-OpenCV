"""Create a local source archive, excluding uploads, environments and credentials."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root=Path(__file__).resolve().parents[1]
out=root/'artifacts/scanpilot-source.zip'
out.parent.mkdir(exist_ok=True)
files=[]
for name in ['app','static','tests','tools','docs','demo','infra']:
    files.extend(p for p in (root/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
files.extend(root/name for name in ['README.md','PROJECT_BRIEF.md','requirements.txt','requirements-dev.txt','requirements-lock.txt',
                                  'Dockerfile','.dockerignore','.gitignore','hackathon-master-prompt (3).md'])
with ZipFile(out,'w',ZIP_DEFLATED) as archive:
    for path in sorted(files):archive.write(path,path.relative_to(root))
print(f'{len(files)} files packaged: {out} ({out.stat().st_size} bytes)')
