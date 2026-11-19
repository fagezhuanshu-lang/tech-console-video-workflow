#!/usr/bin/env python3
"""Portable launcher for five author-native MotionGit portrait packages.

Uses the student's own .motion package and its officially verified helper.
No render implementation, credential, protected content or template is bundled.
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

CATALOG = Path(__file__).with_name('templates.json')
ALIASES = {'characters': 'character'}


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('Official metadata redirected; refusing to execute helper')


def metadata(version):
    if not re.fullmatch(r'1\.0\.0-rc\.[1-9][0-9]*', version):
        raise ValueError('Unsupported helper version; read the new official bootstrap contract')
    url = f'https://motiongit.com/assets/motion-runtimes/{version}.json'
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(urllib.request.Request(url, headers={'User-Agent': 'MotionGit/1.0'}), timeout=30) as r:
        data = r.read(65537)
        if r.status != 200 or len(data) > 65536:
            raise RuntimeError('Invalid official metadata response')
    meta = json.loads(data)
    if (meta.get('profile') != 'motiongit.assistant-runtime/1'
            or meta.get('helperVersion') != version
            or not isinstance(meta.get('bytes'), int) or not 0 < meta['bytes'] <= 4 * 1024 * 1024
            or not re.fullmatch('[a-f0-9]{64}', meta.get('sha256', ''))):
        raise RuntimeError('Invalid official metadata')
    return meta


def private_dir(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == 'nt':
        result = subprocess.check_output(['whoami', '/user', '/fo', 'csv', '/nh'], text=True)
        sid = next(csv.reader(io.StringIO(result.strip())))[1]
        if not re.fullmatch(r'S-1-[0-9-]+', sid):
            raise RuntimeError('Could not determine current Windows user SID')
        subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', f'*{sid}:(OI)(CI)F'],
                       check=True, stdout=subprocess.DEVNULL)
    else:
        path.chmod(0o700)


def environment(work):
    env = dict(os.environ)
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    temp = work / 'temp'
    temp.mkdir(exist_ok=True)
    env['TEMP'] = env['TMP'] = env['TMPDIR'] = str(temp)
    return env


def invoke(node, helper, words, work, name, echo=False):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    log = work / 'logs' / f'{stamp}-{name}.log'
    log.parent.mkdir(exist_ok=True)
    # Never build a shell command or send account data ourselves.
    with log.open('wb') as f:
        p = subprocess.run([node, str(helper), *map(str, words)], env=environment(work), stdout=f, stderr=subprocess.STDOUT)
    data = log.read_bytes().decode('utf-8', errors='replace')
    print(json.dumps({'stage': name, 'exitCode': p.returncode, 'privateLog': str(log)}, ensure_ascii=False), file=sys.stderr)
    if p.returncode:
        if 'cache or secret path rejected' in data:
            print('Official native entry rejected a runtime path. Stop this stage and retain the log; see KNOWN-ISSUES.md.', file=sys.stderr)
        raise SystemExit(p.returncode)
    return data


def initialize(args, spec, work):
    package = Path(args.package).resolve(strict=True)
    if work.exists():
        raise ValueError('Use a fresh work directory for init; existing production is preserved')
    private_dir(work)
    with zipfile.ZipFile(package) as z:
        names = z.namelist()
        for name in ['00-START-HERE.md', 'assistant/guide.json', 'assistant/motion.mjs']:
            if names.count(name) != 1:
                raise ValueError(f'Missing or duplicate public bootstrap entry: {name}')
        if z.getinfo('assistant/guide.json').file_size > 1024 * 1024:
            raise ValueError('Bootstrap guide too large')
        guide = json.loads(z.read('assistant/guide.json'))
        meta = metadata(guide['helperVersion'])
        if z.getinfo('assistant/motion.mjs').file_size != meta['bytes']:
            raise ValueError('Helper size does not match official metadata')
        helper_bytes = z.read('assistant/motion.mjs')
    if hashlib.sha256(helper_bytes).hexdigest() != meta['sha256']:
        raise ValueError('Helper SHA256 does not match official metadata')
    helper = work / 'motion.mjs'
    helper.write_bytes(helper_bytes)
    node = args.node or shutil.which('node')
    if not node:
        raise ValueError('Node.js is required on PATH, or provide --node')
    version = subprocess.check_output([node, '--version'], text=True).strip()
    if int(version.lstrip('v').split('.')[0]) < max(22, int(meta.get('minimumNode', 22))):
        raise ValueError('Node.js 22+ is required')
    started = json.loads(invoke(node, helper, ['start', package, '--summary'], work, 'start', echo=False))
    identity = started.get('assistantGuide', {}).get('template', {})
    if (started.get('verified') is not True or identity.get('id') != spec['slug']
            or identity.get('version') not in spec.get('acceptedVersions', [spec['version']])):
        raise ValueError('Verified package identity does not match the selected template')
    if identity.get('width') != 1080 or identity.get('height') != 1920:
        raise ValueError('Package is not the declared 1080x1920 portrait template')
    created = json.loads(invoke(node, helper, ['new', package, work / 'instance'], work, 'new', echo=False))
    if created.get('templateId') != spec['id']:
        raise ValueError('Verified numeric template ID differs from catalog')
    state = {'profile': 'portrait-five.native-launcher/1', 'template': args.template,
             'slug': identity['id'], 'version': identity['version'],
             'package': str(package), 'packageSha256': digest(package),
             'helperSha256': meta['sha256'], 'helperVersion': meta['helperVersion'],
             'node': str(Path(node).resolve()), 'instance': str(work / 'instance')}
    save_json(work / 'state.json', state)
    print(json.dumps({'status': 'initialized', 'template': state['slug'], 'version': state['version'],
                      'instance': state['instance'], 'nativeRenderVerified': False}, ensure_ascii=False, indent=2))


def main():
    catalog = read_json(CATALOG)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--template', type=lambda value: ALIASES.get(value, value), choices=list(catalog['templates']))
    p.add_argument('--work', type=Path, help='Private production directory; use E: on this workstation')
    p.add_argument('--package', help='Your own original personal .motion; needed for init')
    p.add_argument('--node', help='Node.js executable; needed only when not on PATH')
    p.add_argument('action', choices=['list', 'init', 'read', 'run'])
    p.add_argument('arguments', nargs=argparse.REMAINDER)
    args = p.parse_args()
    if args.action == 'list':
        print(json.dumps(catalog, ensure_ascii=False, indent=2)); return
    if not args.work or (args.action == 'init' and (not args.template or not args.package)):
        p.error('--work is required; init also requires --template and --package')
    work = args.work.resolve()
    if args.action == 'init':
        initialize(args, catalog['templates'][args.template], work); return
    state = read_json(work / 'state.json')
    if args.template and args.template != ALIASES.get(state['template'], state['template']):
        raise ValueError('Selected template differs from initialized instance')
    helper, package = work / 'motion.mjs', Path(state['package'])
    if digest(helper) != state['helperSha256'] or digest(package) != state['packageSha256']:
        raise ValueError('Package or helper changed; initialize the new version in a fresh work directory')
    words = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    if args.action == 'read':
        if len(words) != 1:
            p.error('read takes one public document path from the verified guide')
        invoke(state['node'], helper, ['read', package, words[0]], work, 'read')
        return
    allowed = {'doctor', 'setup', 'capabilities', 'check-params', 'plan', 'prepare', 'preview', 'render'}
    if not words or words[0] not in allowed:
        p.error('run must start with a declared native stage: ' + ', '.join(sorted(allowed)))
    if any(w == '--workflow' or w.startswith('--workflow=') for w in words):
        p.error('This launcher uses the native default workflow; use the separate component entry for motion-kit/poster-kit')
    if words[0] in {'check-params', 'plan'}:
        if len(words) < 2:
            p.error('A native parameter JSON file is required')
        params = read_json(words[1])
        if params.get('workflow') not in (None, 'native') or 'timeline' in params:
            raise ValueError('Component parameters cannot be accepted as native choreography')
    invoke(state['node'], helper, ['run', package, '--instance', state['instance'], *words], work, words[0])


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'Native launcher: {exc}', file=sys.stderr)
        raise SystemExit(2)
