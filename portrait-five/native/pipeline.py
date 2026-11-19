#!/usr/bin/env python3
"""Stage and resume a native production through the verified run.py launcher."""
import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode = True
import run as launcher

HERE = Path(__file__).resolve().parent

def put(source, target):
    if source.is_symlink() or not source.is_file():
        raise ValueError(f'Expected a regular input file: {source}')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if launcher.digest(source) != launcher.digest(target):
            raise ValueError(f'Conflicting input: {target.name}; --inputs and main media must have identical bytes when filenames overlap')
        return
    shutil.copy2(source, target)

def call(job, work, *words):
    env = dict(os.environ, LOCALAPPDATA=job['runtimeRoot'],
               PLAYWRIGHT_BROWSERS_PATH=str(Path(job['runtimeRoot'])/'ms-playwright'))
    dirs = [str(Path(sys.executable).parent)]
    dirs.extend(str(Path(job[k]).parent) for k in ('ffmpeg','ffprobe','node','npm'))
    env['PATH'] = os.pathsep.join(dirs + [env.get('PATH','')])
    return subprocess.run([sys.executable,str(HERE/'run.py'),'--work',str(work),*map(str,words)],env=env).returncode

def stage(job, work, *words):
    if call(job,work,'run',*words,'--language','zh'):
        raise RuntimeError(f'Official {words[0]} failed; retain the private log and resume only after resolving it')

def inspect_media(job, path):
    data=json.loads(subprocess.check_output([job['ffprobe'],'-v','error','-show_streams','-show_format','-of','json',str(path)]))
    if not any(s.get('codec_type')=='audio' for s in data['streams']):
        raise ValueError('The supplied video must contain its original narration audio')
    return data

def validate_captions(rows, duration, params):
    normalize=lambda s:re.sub(r'[^\w]+','',s).lower()
    if not isinstance(rows,list) or not rows:
        raise ValueError('Captions must be a nonempty array in the bilingual word-time example format')
    previous=0
    for row in rows:
        start,end=float(row['t0']),float(row['t1']); words=row['highlight']['units']
        if not row.get('zh') or not row.get('en') or not words or not previous<=start<end<=duration+0.1:
            raise ValueError('Invalid bilingual caption or cue timing')
        last=start
        for word in words:
            a,b=float(word['start']),float(word['end'])
            if not word.get('text') or not start-0.02<=a<b<=end+0.02 or a<last-0.02:
                raise ValueError('Invalid measured word timing; use actual ASR/alignment records')
            last=a
        previous=end
        if normalize(''.join(w['text'] for w in words))!=normalize(row['zh']):
            raise ValueError('Word records must cover the actual complete Chinese caption')
    if normalize(''.join(r['zh'] for r in rows))!=normalize(params['brief']['contentEvidence']['text']):
        raise ValueError('The complete Chinese captions and current contentEvidence text differ')

def approve(path, flag):
    receipt=launcher.read_json(path)
    if receipt.get('reviewed') is True:return True
    if not flag:return False
    receipt['reviewed']=True;launcher.save_json(path,receipt);return True

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--style',type=lambda s:launcher.ALIASES.get(s,s),choices=list(launcher.read_json(HERE/'templates.json')['templates']))
    p.add_argument('--package',type=Path);p.add_argument('--video','--talk',dest='video',type=Path)
    p.add_argument('--captions',type=Path);p.add_argument('--params',type=Path)
    p.add_argument('--inputs',type=Path);p.add_argument('--output',type=Path)
    p.add_argument('--runtime-root',type=Path)
    for tool in ('node','ffmpeg','ffprobe','npm'):p.add_argument('--'+tool)
    p.add_argument('--stage',choices=['plan','preview','render'],default='plan')
    p.add_argument('--approve-plan',action='store_true',help='Set only after actual plan review by the user or assistant')
    p.add_argument('--approve-preview',action='store_true',help='Set only after actual preview review by the user or assistant')
    args=p.parse_args();work=args.work.resolve();record=work/'pipeline.json'
    if not record.exists():
        if not all((args.style,args.package,args.video,args.captions,args.params,args.output)):
            p.error('First run requires --style --package --video --captions --params --output')
        if work.exists():raise ValueError('First run requires a new --work directory')
        if args.output.exists():raise ValueError('Output already exists; choose a new path')
        job={'style':args.style,'output':str(args.output.resolve()),'runtimeRoot':str((args.runtime_root or work.parent/'native-runtime').resolve())}
        for tool in ('node','ffmpeg','ffprobe','npm'):
            found=getattr(args,tool) or shutil.which(tool)
            if not found:raise ValueError(f'{tool} missing; install the declared requirement or supply --{tool}')
            job[tool]=str(Path(found).resolve(strict=True))
        media=inspect_media(job,args.video);duration=float(media['format']['duration'])
        params=launcher.read_json(args.params);captions=launcher.read_json(args.captions)
        validate_captions(captions,duration,params)
        if call(job,work,'--template',args.style,'--package',args.package.resolve(),'--node',job['node'],'init'):
            raise RuntimeError('Verified initialization failed')
        inputs=work/'instance/inputs';inputs.mkdir(exist_ok=True)
        if args.inputs:
            extra=args.inputs.resolve(strict=True)
            for source in sorted(extra.rglob('*')):
                if source.is_symlink():raise ValueError('Extra inputs may not contain symbolic links')
                if source.is_file():put(source,inputs/source.relative_to(extra))
        # Keep the native params' relative filenames, allowing matching extra-input files.
        for key,source in (('talk',args.video),('captions',args.captions)):
            relative=Path(params['media'][key])
            if relative.is_absolute() or '..' in relative.parts:raise ValueError('Native media paths must stay within --inputs')
            put(source.resolve(strict=True),inputs/relative)
        launcher.save_json(work/'instance/params.json',params)
        job.update(narrationDuration=duration,phase='initialized',inputHashes={f.relative_to(inputs).as_posix():launcher.digest(f) for f in inputs.rglob('*') if f.is_file()},paramsSha256=launcher.digest(work/'instance/params.json'))
        launcher.save_json(record,job)
    else:
        job=launcher.read_json(record)
        if args.npm:
            job['npm']=str(Path(args.npm).resolve(strict=True));launcher.save_json(record,job)
        if args.style and args.style!=job['style']:raise ValueError('Resume style differs from the original job')
        if any((args.package,args.video,args.captions,args.params,args.inputs,args.output,args.runtime_root,args.node,args.ffmpeg,args.ffprobe)):
            p.error('Resume uses recorded inputs/tools; pass only --work, --stage and actual review flags')
    inst=work/'instance';plan=inst/'pipeline-plan';project=inst/'pipeline-project'
    if launcher.digest(inst/'params.json')!=job['paramsSha256']:raise ValueError('Parameters changed; create a new work directory')
    for name,sha in job['inputHashes'].items():
        if launcher.digest(inst/'inputs'/name)!=sha:raise ValueError('Input changed; create a new work directory')
    def checkpoint(phase):
        job['phase']=phase;launcher.save_json(record,job)
    if job['phase']=='initialized':
        if call(job,work,'run','doctor','--language','zh'):
            last=sorted((work/'logs').glob('*doctor.log'))[-1].read_text(encoding='utf-8',errors='replace')
            if 'cache or secret path rejected' in last:
                raise RuntimeError('This official release has the known native path error; see KNOWN-ISSUES.md and preserve this work directory')
            stage(job,work,'setup');stage(job,work,'doctor')
        checkpoint('dependencies-ready')
    if job['phase']=='dependencies-ready':
        stage(job,work,'check-params',inst/'params.json','--inputs',inst/'inputs')
        stage(job,work,'plan',inst/'params.json','--inputs',inst/'inputs','--out',plan)
        spec=launcher.read_json(plan/'spec.json')
        if spec.get('adaptation',{}).get('ready') is not True or not spec.get('scenes'):
            raise ValueError(f'Plan is not ready; inspect {plan / "report.md"}; revise in a new work directory')
        length=max(s['endFrame'] for s in spec['scenes'])/spec['fps']
        if length+0.05<job['narrationDuration']:raise ValueError('Plan would truncate the supplied narration')
        timing=launcher.read_json(plan/'narration-map.json')
        if timing.get('timingCoverageVerified') is not True:raise ValueError('Native narration timing coverage has not passed')
        job['plannedFrames']=max(s['endFrame'] for s in spec['scenes']);job['fps']=spec['fps']
        checkpoint('plan-ready')
    if args.stage=='plan':
        print(json.dumps({'status':'plan-ready','review':str(plan/'report.md'),'next':'Review plan, then resume --stage preview --approve-plan'}));return
    if not approve(plan/'review.json',args.approve_plan):
        print(json.dumps({'status':'plan-review-required','review':str(plan/'report.md')}));return
    if job['phase']=='plan-ready':
        stage(job,work,'prepare','@vault','--inputs','@vault','--plan',plan,'--out',project)
        checkpoint('prepared')
    if job['phase']=='prepared':
        spec=launcher.read_json(plan/'spec.json');points=set();fps=job['fps']
        for scene in spec['scenes']:
            a,b=scene['startFrame']/fps,scene['endFrame']/fps
            points.update(round(t,3) for t in (a+.05,a+.8,a+1.8,(a+b)/2,b-2/fps) if a<=t<b)
            points.update(round(cue['frame']/fps+.1,3) for cue in scene.get('cues',{}).values() if a<=cue['frame']/fps+.1<b)
        times=','.join(map(str,sorted(points)))
        stage(job,work,'preview',project,'--times',times)
        checkpoint('preview-ready')
    if args.stage=='preview':
        print(json.dumps({'status':'preview-ready','review':str(project/'preview.json'),'stills':str(project/'stills'),'next':'Inspect actual frames, then resume --stage render --approve-preview'}));return
    if not approve(project/'preview.json',args.approve_preview):
        print(json.dumps({'status':'preview-review-required','review':str(project/'preview.json')}));return
    movie=inst/'native-output.mp4'
    if job['phase']=='preview-ready':
        stage(job,work,'render',project,'--out',movie);checkpoint('rendered')
    encoded=inspect_media(job,movie);streams=encoded['streams'];video=next(s for s in streams if s['codec_type']=='video')
    if (video['width'],video['height'],video['avg_frame_rate'],int(video['nb_frames']))!=(1080,1920,'60/1',job['plannedFrames']):
        raise ValueError('Encoded video dimensions, frame rate or frame count differ from the reviewed plan')
    if float(encoded['format']['duration'])+0.05<job['narrationDuration']:raise ValueError('Encoded output truncates narration')
    subprocess.run([job['ffmpeg'],'-nostdin','-v','error','-xerror','-i',str(movie),'-f','null','-'],check=True)
    target=Path(job['output']);put(movie,target)
    verification={'workflow':'native','template':job['style'],'version':launcher.read_json(work/'state.json')['version'],'sha256':launcher.digest(target),'width':video['width'],'height':video['height'],'frames':int(video['nb_frames']),'fps':60,'duration':float(encoded['format']['duration']),'audioPresent':True,'fullDecode':'passed','reviewScope':'Plan and preview were explicitly approved; final artistic/audio listening review remains with the user or assistant.'}
    launcher.save_json(target.with_suffix(target.suffix+'.verification.json'),verification);checkpoint('complete')
    print(json.dumps({'status':'complete','output':str(target),'verification':str(target.with_suffix(target.suffix+'.verification.json'))},ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.CalledProcessError) as exc:
        print(f'Native pipeline: {exc}',file=sys.stderr);raise SystemExit(2)
