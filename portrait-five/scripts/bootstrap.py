"""Check the host and prepare dependencies through the user's own MotionGit package."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

import native

from presets import RELEASE_HASHES, STYLES


def executable(value):
    resolved = shutil.which(value)
    if not resolved and Path(value).is_file():
        resolved = str(Path(value).resolve())
    return resolved


def host_report(args):
    report = {'platform':sys.platform, 'python':{'path':sys.executable, 'version':list(sys.version_info[:3]),
              'ok':sys.version_info >= (3,12)}, 'tools':{}, 'checks':{}, 'missing':[]}
    if not report['python']['ok']:
        report['missing'].append('Python 3.12 or later is required by the tested template runtime')
    for name in ('node','ffmpeg','ffprobe'):
        path = executable(getattr(args,name))
        report['tools'][name] = path
        if not path:
            report['missing'].append(f'{name}: executable not found; install it or pass --{name}')
            continue
        try:
            proc = subprocess.run([path, '--version' if name=='node' else '-version'],
                                  capture_output=True,text=True,timeout=20,check=True)
            version = (proc.stdout or proc.stderr).splitlines()[0]
            report['checks'][name] = {'ok':True,'version':version}
            if name=='node':
                parsed = re.match(r'v(\d+)\.(\d+)\.(\d+)',version)
                if not parsed or tuple(map(int,parsed.groups())) < (22,12,0):
                    report['checks'][name]['ok'] = False
                    report['missing'].append('Node.js 22.12 or later is required')
            elif name=='ffmpeg':
                enc = subprocess.check_output([path,'-hide_banner','-encoders'],stderr=subprocess.STDOUT,text=True,timeout=20)
                has_x264 = bool(re.search(r'\blibx264\b',enc))
                report['checks'][name]['libx264'] = has_x264
                if not has_x264:
                    report['missing'].append('FFmpeg must include the libx264 encoder')
        except (OSError,subprocess.SubprocessError) as exc:
            report['checks'][name] = {'ok':False,'error':type(exc).__name__}
            report['missing'].append(f'{name}: version check failed')
    node = report['tools'].get('node')
    npm = shutil.which('npm')
    if not npm and node:
        candidate=Path(node).parent / ('npm.cmd' if os.name=='nt' else 'npm')
        if candidate.is_file():
            npm=str(candidate)
    report['tools']['npm'] = npm
    if not npm:
        report['missing'].append('npm is missing; use the standard Node.js installation with npm')
    report['host_ready'] = not report['missing']
    report['template_ready'] = None
    report['scope'] = 'Host-only diagnosis; a personal package is required to verify template dependencies'
    return report


def template_setup(args, report):
    native.require(args.style and args.work, '--template requires --style and a new --work directory')
    native.require(args.template.is_file(), 'Personal .motion package not found')
    work = native.make_private_dir(args.work)
    cache = native.configure_environment(args.cache or work / 'cache')
    tool_dirs = [str(Path(sys.executable).parent)]
    tool_dirs += [str(Path(p).parent) for p in report['tools'].values() if p]
    os.environ['PATH'] = os.pathsep.join([*dict.fromkeys(tool_dirs), os.environ.get('PATH','')])
    logs=work/'private-logs'
    logs.mkdir()
    entry=[report['tools']['node'],str(native.verify_helper(args.template,work))]
    package=str(args.template.resolve())
    start=native.read(native.private_run(entry+['start',package,'--summary'],logs,'start'))
    native.require(start.get('verified') is True,'Personal package signature verification failed')
    created=native.read(native.private_run(entry+['new',package,str(work/'instance')],logs,'new'))
    settings = STYLES[args.style]
    slug, template_id = settings['slug'], settings['id']
    version, workflow = settings['version'], settings['workflow']
    native.require(created.get('template') == f'{slug}@{version}' and created.get('templateId') == template_id,
                   f'Expected {slug}@{version}; use the matching personal package')
    native.require(created.get('releaseArchiveSha256') == RELEASE_HASHES[args.style],
                   'The signed release differs from the reviewed version')
    instance=Path(created['instanceDirectory']).resolve()
    native.require(instance == (work/'instance').resolve(), 'Unexpected instance directory')
    prefix=entry+['run',package,'--instance',str(instance),'--cache',str(cache)]
    report.update(style=args.style,template=f'{slug}@{version}',workflow=workflow,
                  cache=str(cache),private_work=str(work),package_verified=True)
    if workflow=='poster-kit':
        if args.action=='doctor':
            report.update(template_ready=None,scope='Host and package identity verified; poster-kit declares setup, not a dependency doctor',
                          next_step='Run setup with this style and package in a new work directory; official setup confirms dependenciesReady')
        else:
            setup=native.read(native.private_run(prefix+['setup','--workflow',workflow,'--language','zh'],logs,'setup'))
            native.require(setup.get('workflow')=='poster-kit' and setup.get('dependenciesReady') is True,
                           'Official poster-kit setup did not confirm dependenciesReady; inspect the private log')
            report.update(template_ready=True,scope='Host and official poster-kit setup readiness verified')
        native.save(work/'bootstrap-report.json',report)
        return
    if args.action=='setup':
        native.private_run(prefix+['setup','--workflow',workflow,'--language','zh'],logs,'setup')
    doctor=native.read(native.private_run(prefix+['doctor','--workflow',workflow,'--language','zh'],logs,'doctor'))
    ready=doctor.get('status')=='dependencies-verified'
    native.require(ready,'Official dependency doctor did not confirm readiness; inspect the private log')
    report.update(template_ready=True,style=args.style,template=f'{slug}@{version}',workflow=workflow,
                  cache=str(cache),private_work=str(work),scope='Host and official component-workflow dependencies verified')
    native.save(work/'bootstrap-report.json', report)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['doctor','setup'])
    parser.add_argument('--style',choices=STYLES)
    parser.add_argument('--template',type=Path)
    parser.add_argument('--work',type=Path,help='New private directory; never use a repository or existing project')
    parser.add_argument('--cache',type=Path,help='Short writable cache path, e.g. E:/MotionGitCache')
    for key in ('node','ffmpeg','ffprobe'):
        parser.add_argument('--'+key,default=key)
    args=parser.parse_args()
    if args.action=='setup' and not args.template:
        parser.error('setup requires --template, --style and --work; system applications are not silently installed')
    report=host_report(args)
    try:
        if args.template:
            native.require(report['host_ready'],'Install the missing host dependencies listed in this report first')
            template_setup(args,report)
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.SubprocessError,zipfile.BadZipFile) as exc:
        report.update(template_ready=False,error=str(exc))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['host_ready'] and report['template_ready'] is not False else 1


if __name__=='__main__':
    raise SystemExit(main())
