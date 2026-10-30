#!/usr/bin/env python3
"""Original vertical coffee concept edit using properly attributed real moving footage.
No paid provider, no publishing, no third-party music.
"""
import json,os,subprocess,requests
from pathlib import Path
from urllib.parse import quote,urlsplit,urlunsplit
from PIL import Image,ImageFont,ImageDraw,ImageFilter
import numpy as np,wave,math

ROOT=Path('output-selling-concept');ROOT.mkdir(exist_ok=True)
name='File:Macro Espresso Process.webm'
url='https://commons.wikimedia.org/w/api.php'
r=requests.get(url,params={'action':'query','format':'json','formatversion':'2','titles':name,'prop':'imageinfo','iiprop':'url|extmetadata|mime|size'},headers={'User-Agent':'NonCommercial-ConceptProof/1.0 (Wikimedia attribution preserved)'},timeout=25)
r.raise_for_status()
data=r.json()['query']['pages'][0]
inf=data['imageinfo'][0]
meta=inf.get('extmetadata') or {}
license_name=meta.get('LicenseShortName',{}).get('value','')
if license_name.lower().strip() not in ('cc-by-2.0','cc by 2.0','attribution 2.0 generic'):
    raise RuntimeError('License not verified: '+license_name)
if inf.get('mime')!='video/webm':raise RuntimeError('unexpected source MIME')
source=ROOT/'macro_espresso_source.webm'
clean_url=urlunsplit(urlsplit(inf['url'])._replace(query='',fragment=''))
transcode_url='https://upload.wikimedia.org/wikipedia/commons/transcoded/6/66/Macro_Espresso_Process.webm/Macro_Espresso_Process.webm.480p.vp9.webm'
with requests.get(transcode_url,stream=True,timeout=55,headers={'User-Agent':'Mozilla/5.0 (nonpublishing concept render)'}) as rr:
    rr.raise_for_status()
    count=0
    with source.open('wb') as fh:
        for part in rr.iter_content(131072):
            if part:
                count+=len(part)
                if count>55_000_000:raise ValueError('source too large')
                fh.write(part)
if source.stat().st_size<500000:raise RuntimeError('source video empty')
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(source)]))
duration=float(probe['format']['duration'])
if duration<31.5:raise RuntimeError('insufficient motion footage')
# 6 genuine motion shots from distinct moments of one licensed original film.
shots=[(1.0,2.0),(5.6,1.8),(10.0,1.9),(17.0,2.0),(22.0,2.2),(29.2,2.1)]
if max(a+b for a,b in shots)>duration:raise RuntimeError('source too short')
font='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
normal='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
def overlay(idx,hook):
    image=Image.new('RGBA',(720,1280),(0,0,0,0))
    d=ImageDraw.Draw(image)
    d.rectangle((0,0,720,140),fill=(4,7,10,155))
    d.rectangle((0,1030,720,1280),fill=(4,7,10,170))
    d.text((42,47),'ROAST / RITUAL',font=ImageFont.truetype(font,41),fill=(239,218,178))
    d.rectangle((42,1050,150,1054),fill=(226,187,110))
    d.text((43,1090),hook,font=ImageFont.truetype(font,44),fill=(255,249,233))
    d.text((44,1180),'CONCEPT FILM  |  架空ブランド',font=ImageFont.truetype(normal,21),fill=(215,215,211))
    if idx==5:
        d.rectangle((0,0,720,1280),fill=(2,4,7,55))
    dst=ROOT/f'overlay_{idx}.png';image.save(dst);return dst
words=['この一滴が、','目を離せない。','香りの、その先へ。','一杯へのこだわり。','余韻を、味わう。','次の一杯が、楽しみになる。']
pieces=[]
for i,(ss,dur) in enumerate(shots):
    over=overlay(i,words[i]); out=ROOT/f'shot_{i}.mp4'
    # Actual video (crop/scale) and subtle non-copyrighted editorial overlay
    vf='[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,eq=contrast=1.1:saturation=0.9,setsar=1[base];[base][1:v]overlay=0:0:format=auto,format=yuv420p[v]'
    subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-y','-ss',str(ss),'-i',str(source),'-loop','1','-i',str(over),
                    '-filter_complex',vf,'-map','[v]','-an','-t',str(dur),'-r','24','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',str(out)],check=True)
    pieces.append(out)
concat=ROOT/'concat.txt'
concat.write_text(''.join("file '"+p.name+"'\n" for p in pieces))
silent=ROOT/'silent.mp4'
subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),
                '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',str(silent)],check=True)
# Fully synthetic original ambient pulse audio; no commercial soundtrack license.
total=sum(x[1] for x in shots);sr=24000
arr=np.zeros(int(sr*total),dtype=np.float64)
for i in range(0,int(total*2)):
    start=int(i*.5*sr)
    length=min(len(arr)-start,int(.38*sr))
    if length<=0:break
    t=np.arange(length)/sr
    amp=(.020 if i%2 else .033)*np.exp(-12*t)
    arr[start:start+length]+=amp*np.sin(2*np.pi*(90 if i%2 else 110)*t)
for f in (146.83,196,246.94):
    arr+=0.008*np.sin(2*np.pi*f*np.arange(len(arr))/sr)*np.sin(np.pi*np.arange(len(arr))/len(arr))**2
arr*=np.minimum(1,np.arange(len(arr))/(sr*.5))*np.minimum(1,(len(arr)-np.arange(len(arr)))/(sr*.8))
wav=ROOT/'original_music.wav'
with wave.open(str(wav),'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((np.clip(arr,-1,1)*32767).astype('<i2').tobytes())
final=ROOT/'roast_ritual_concept.mp4'
subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-y','-i',str(silent),'-i',str(wav),
                '-c:v','copy','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(final)],check=True)
report={
  'name':'ROAST / RITUAL — original coffee concept video',
  'draft_for_sales_pitch':True,'not_real_client':True,'social_posted':False,'commercial_client_approval':False,
  'source':'https://commons.wikimedia.org/wiki/File:Macro_Espresso_Process.webm',
  'creator':'Scott Schiller','license':'Creative Commons Attribution 2.0 Generic',
  'license_url':'https://creativecommons.org/licenses/by/2.0/',
  'changes':'Re-edited six motion segments, crop to vertical, color adjustment, Japanese original copy, overlays, synthetic music',
  'source_file_downloaded':source.stat().st_size,'duration_seconds':total,
  'reference':'research/viral_food_benchmarks_2026-10.json',
  'notes':'Editorial sample only. Attribution included in supplied README; avoid brand endorsement. Commercial redistribution requires credit/rights check.',
  'additional_paid_charge_jpy':0,'runway_credit_use':0
}
(ROOT/'credits_and_rights.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
(ROOT/'ATTRIBUTION.txt').write_text(
    'Video footage: Macro Espresso Process by Scott Schiller (CC BY 2.0).\n'
    'https://commons.wikimedia.org/wiki/File:Macro_Espresso_Process.webm\n'
    'License: https://creativecommons.org/licenses/by/2.0/\n'
    'Edited: temporal cuts, vertical crop, color grading, typography, original audio.\n'
    'ROAST / RITUAL is a fictional demonstration brand, not a real cafe endorsement.\n')
meta2=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(final)]))
assert {'video','audio'}<=set(x['codec_type'] for x in meta2['streams'])
assert any(x.get('width')==720 and x.get('height')==1280 for x in meta2['streams'])
print('FINISHED',final,'duration',total,'source_bytes',source.stat().st_size)
