#!/usr/bin/env python3
"""Owner-licensed long video -> Shorts: motion-ranked excerpts, no publishing."""
import argparse, json, subprocess, math, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W,H,FPS=720,1280,24
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
ALLOWED={'owned','written_permission','cc0','public_domain','cc_by'}
def check_rights(r):
    if r.get('rights_basis') not in ALLOWED or r.get('commercial_use_allowed') is not True:
        raise ValueError('Reuse rights not explicitly confirmed')
    for k in ('title','creator','source_url'):
        if not r.get(k):raise ValueError('Missing rights field: '+k)
    if r['rights_basis']=='owned' and r.get('ownership_confirmed') is not True:
        raise ValueError('Owner must confirm full rights')
    if r['rights_basis']=='written_permission' and (not r.get('permission_evidence') or not r.get('permission_scope')):
        raise ValueError('Written permission evidence and scope required')
    if r['rights_basis']=='cc_by' and (not r.get('license_url') or not r.get('attribution')):
        raise ValueError('CC BY requires attribution and license URL')
    if r.get('contains_unlicensed_music') is not False:
        raise ValueError('Unlicensed music must be excluded/rights-checked')
    return r
def duration_of(path):
    x=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)]))
    d=float(x['format']['duration'])
    if d<12 or d>10800 or not any(s.get('codec_type')=='video' for s in x['streams']):
        raise ValueError('Video must be a real movie of 12 seconds to 3 hours')
    return d
def scores_of(path,limit=900):
    raw=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(path),'-t',str(limit),
                                  '-vf','fps=1,scale=80:80','-f','rawvideo','-pix_fmt','gray','pipe:1'])
    n=len(raw)//6400
    if n<10:raise ValueError('Video too short to analyze')
    frames=np.frombuffer(raw[:n*6400],np.uint8).reshape(n,80,80).astype(np.float32)
    movement=np.abs(frames[1:]-frames[:-1]).mean((1,2))
    return (.8*np.r_[movement[0],movement]+.15*frames.std((1,2))).tolist()
def find_moments(scores,duration,n=5,seconds=2.4):
    if not 2<=n<=8:raise ValueError('Count must be 2 to 8')
    choices=[]
    for t in np.arange(.5,min(duration,len(scores))-seconds-.2,.6):
        a=int(t);b=min(len(scores),int(math.ceil(t+seconds)))
        if b-a<2:continue
        choices.append((float(np.mean(scores[a:b])),round(float(t),2)))
    choices.sort(reverse=True)
    chosen=[]
    for sc,t in choices:
        if all(abs(t-tt)>=seconds+.8 for _,tt in chosen):
            chosen.append((sc,t))
            if len(chosen)==n:break
    if len(chosen)<2:raise ValueError('Cannot find distinct moments')
    arranged=[chosen[0]]+sorted(chosen[1:],key=lambda z:z[1])
    return [{'start':t,'duration':seconds,'motion_score':round(sc,2)} for sc,t in arranged]
def overlay(path,index,total,headline,title):
    image=Image.new('RGBA',(W,H))
    dr=ImageDraw.Draw(image)
    dr.rectangle((0,0,W,135),fill=(9,11,14,152))
    dr.rectangle((0,1030,W,H),fill=(9,11,14,182))
    f=ImageFont.truetype(FONT,39)
    dr.text((40,46),'SHORTS / HIGHLIGHT',font=ImageFont.truetype(FONT,25),fill=(245,208,159))
    dr.text((540,46),f'{index+1:02d}/{total:02d}',font=ImageFont.truetype(FONT,26),fill='white')
    dr.text((40,1078),headline[:18],font=f,fill='white')
    dr.text((40,1174),title[:26],font=ImageFont.truetype(FONT,21),fill=(218,205,189))
    image.save(path)
def audio(path,duration,cuts):
    sr=24000;t=np.arange(int(sr*duration))/sr
    a=.014*np.sin(2*np.pi*164.8*t)*np.sin(np.pi*t/duration)**2
    a+=.008*np.sin(2*np.pi*220*t)*np.sin(np.pi*t/duration)**2
    for at in cuts:
        st=int(at*sr);length=min(int(sr*.26),len(a)-st)
        if length>0:
            u=np.arange(length)/sr
            a[st:st+length]+=.036*np.exp(-19*u)*np.sin(2*np.pi*108*u)
    a*=np.minimum(1,t/.3)*np.minimum(1,(duration-t)/.4)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr)
        w.writeframes((np.clip(a,-1,1)*32767).astype('<i2').tobytes())
def build(source,rights,selected,out,title,headlines):
    out.mkdir(parents=True,exist_ok=True)
    segments=[]
    for i,shot in enumerate(selected):
        png=out/f'caption_{i}.png';overlay(png,i,len(selected),headlines[i%len(headlines)],title)
        clip=out/f'clip_{i}.mp4'
        flt='[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1[base];[base][1:v]overlay=0:0,format=yuv420p[v]'
        subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-ss',str(shot['start']),'-i',str(source),
                        '-loop','1','-i',str(png),'-filter_complex',flt,'-map','[v]',
                        '-an','-t',str(shot['duration']),'-r',str(FPS),
                        '-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',str(clip)],check=True)
        segments.append(clip)
    (out/'concat.txt').write_text(''.join("file '"+p.name+"'\n" for p in segments))
    video=out/'silent.mp4'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-f','concat','-safe','0','-i',
                    str(out/'concat.txt'),'-c','copy',str(video)],check=True)
    dur=sum(s['duration'] for s in selected)
    snd=out/'original.wav';audio(snd,dur,[sum(s['duration'] for s in selected[:i]) for i in range(len(selected))])
    result=out/'shorts_review_draft.mp4'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(video),'-i',str(snd),
                    '-c:v','copy','-c:a','aac','-b:a','128k','-shortest','-movflags',
                    '+faststart',str(result)],check=True)
    (out/'ATTRIBUTION.txt').write_text(
        'Source: '+rights['title']+'\nAuthor: '+rights['creator']+'\nURL: '+rights['source_url']+
        '\nRights: '+rights['rights_basis']+'\nLicense: '+rights.get('license_url','owner confirmed')+
        '\nEdit: automatic highlight selection, 9:16 crop, original text and music.\n'
        'Not approved for automatic publication or resale.\n')
    (out/'quality.json').write_text(json.dumps({
        'segments':selected,'automatic_publication':False,'sales_quality_verified':False,
        'human_review_required':True,'paid_tools_used':False,
        'note':'Motion score suggests moments, not proof of viral quality or creator rights.'},
        ensure_ascii=False,indent=2))
    return result
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',required=True,help='Local, authorized video file; no YouTube watch URL')
    ap.add_argument('--rights',required=True)
    ap.add_argument('--out',default='clipper-output')
    ap.add_argument('--count',type=int,default=5)
    ap.add_argument('--title',default='切り抜き編集サンプル')
    ap.add_argument('--headlines',default='この瞬間。|見せ場。|その続きは？|最後まで注目。')
    args=ap.parse_args()
    source=Path(args.input)
    if not source.is_file():raise SystemExit('Input must be a local authorized video file')
    rights=check_rights(json.loads(Path(args.rights).read_text()))
    dur=duration_of(source)
    moments=find_moments(scores_of(source,min(int(dur),900)),dur,args.count)
    headlines=[s.strip() for s in args.headlines.split('|') if s.strip()]
    if not headlines:raise ValueError('Headlines cannot be empty')
    path=build(source,rights,moments,Path(args.out),args.title,headlines)
    print('CREATED',path,'moments',json.dumps(moments))
if __name__=='__main__':main()
