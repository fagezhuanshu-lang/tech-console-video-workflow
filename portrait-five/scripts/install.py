"""Install one or all five self-contained Codex skills without replacing existing skills."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

STYLES = ('modern','paper','dark','character','poster')
SHARED = ('scripts','native','presets','examples','docs')
ROOT_FILES = ('requirements.txt','LICENSE','README.md')
FORBIDDEN_SUFFIXES = {'.motion','.mp4','.mov','.wav','.mp3','.m4a','.log','.pyc','.pyo','.sqlite','.db','.pem','.key'}
FORBIDDEN_NAMES = {'__pycache__','.git','.env','node_modules','private-logs','work','outputs','cache'}


def safe_copy(source, target):
    if source.is_symlink():
        raise ValueError(f'Symbolic links are not included in skill installation: {source.name}')
    if source.name in FORBIDDEN_NAMES or source.suffix.lower() in FORBIDDEN_SUFFIXES:
        return
    if source.is_dir():
        target.mkdir()
        for child in sorted(source.iterdir()):
            safe_copy(child,target/child.name)
    elif source.is_file():
        shutil.copy2(source,target)


def remove_owned(path, root, token, require_marker):
    if path.is_symlink():
        raise ValueError('Refusing cleanup of a replaced installer directory')
    path,root=path.resolve(),root.resolve()
    if path.parent != root or path.is_symlink():
        raise ValueError('Refusing cleanup outside the installer-owned destination')
    if require_marker and (path/'.install-owner').read_text(encoding='utf-8') != token:
        raise ValueError('Installer ownership marker changed; preserving the directory')
    shutil.rmtree(path)


def install(root, destination, styles):
    root, destination=root.resolve(),destination.resolve()
    for required in ('native.py','render.py','presets.py','bootstrap.py'):
        if not (root/'scripts'/required).is_file():
            raise ValueError(f'Incomplete source checkout: missing scripts/{required}')
    for style in styles:
        name='motiongit-'+style
        if not (root/'skills'/name/'SKILL.md').is_file():
            raise ValueError(f'Incomplete source checkout: missing skills/{name}/SKILL.md')
        if (destination/name).exists():
            raise FileExistsError(f'Existing skill preserved: {destination/name}. Choose another --dest or back it up manually.')
    destination.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.motiongit-five-install-',dir=destination))
    token=uuid.uuid4().hex
    claimed=[]
    try:
        for style in styles:
            name='motiongit-'+style
            folder=staging/name
            folder.mkdir()
            safe_copy(root/'skills'/name/'SKILL.md',folder/'SKILL.md')
            for shared in SHARED:
                source=root/shared
                if source.is_dir():
                    safe_copy(source,folder/shared)
            for file in ROOT_FILES:
                if (root/file).is_file():
                    safe_copy(root/file,folder/file)
            # A receipt covers only public workflow source files, never personal packages/media.
            hashes={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(folder.rglob('*')) if p.is_file()}
            (folder/'installation.json').write_text(json.dumps({'schema':1,'style':style,'files':hashes},indent=2)+'\n',encoding='utf-8')
        # Reserve every destination before committing. mkdir fails instead of replacing any path.
        for style in styles:
            target=destination/('motiongit-'+style)
            target.mkdir()
            claimed.append(target)
            (target/'.install-owner').write_text(token,encoding='utf-8')
        for target in claimed:
            for child in (staging/target.name).iterdir():
                child.rename(target/child.name)
        for target in claimed:
            # The complete installation is committed; marker cleanup is housekeeping.
            try:
                (target/'.install-owner').unlink()
            except OSError:
                pass
        return [str(p) for p in claimed]
    except Exception:
        for target in reversed(claimed):
            if (target/'.install-owner').is_file():
                remove_owned(target,destination,token,True)
            elif target.resolve().parent == destination and not target.is_symlink() and not any(target.iterdir()):
                target.rmdir()
        raise
    finally:
        if staging.exists():
            remove_owned(staging,destination,token,False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    default_home=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))
    parser.add_argument('--dest',type=Path,default=default_home/'skills',help='Codex skills root; existing skills are never replaced')
    parser.add_argument('--style',choices=STYLES,action='append',help='Install only this style; repeat for several; omit for all five')
    args=parser.parse_args()
    try:
        paths=install(Path(__file__).resolve().parents[1],args.dest,list(dict.fromkeys(args.style or STYLES)))
    except (OSError,ValueError) as exc:
        parser.exit(1,f'Installation stopped: {exc}\n')
    print(json.dumps({'installed':paths,'next_step':'Available to Codex on the next turn; use your own personal .motion package.'},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
