#!/usr/bin/env python3
"""No-cost, nonpublishing preview of royalty-free photographic media."""
import argparse, hashlib, io, json, math, re, subprocess, wave
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse
from html import unescape
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

SIZE=(640,1138)
FPS=15
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
ALLOWED={'cc0','cc0 1.0','public domain','public domain mark 1.0','pdm 1.0'}

def permitted(name):
    return str(name).lower().strip() in ALLOWED

def demo_photo(folder):
    from skimage.data import coffee
    p=folder/'photo_01.jpg'
    Image.fromarray(coffee()).save(p,quality=94)
    return [{'file':p.name,'author':'Rachel Michetti','license':'CC0-1.0',
             'source_page':'https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.coffee',
             'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'requires_human_review':False}]

def commons_photos(query,folder,limit=5):
    import requests
    session=requests.Session()
    session.headers.update({'User-Agent':'PRVideoTechnicalPreview/1.0 (nonpublishing)'})
    res=session.get('https://commons.wikimedia.org/w/api.php',
      params={'action':'query','format':'json','formatversion':'2','generator':'search',
              'gsrsearch':'filetype:bitmap '+query,'gsrnamespace':6,'gsrlimit':50,
              'prop':'imageinfo','iiprop':'url|size|mime|extmetadata','iiurlwidth':1100},
      timeout=30)
    res.raise_for_status()
    output=[]
    for page in res.json().get('query',{}).get('pages',[]):
        info=(page.get('imageinfo') or [{}])[0]
        meta=info.get('extmetadata') or {}
        license_name=(meta.get('LicenseShortName') or {}).get('value','')
        if not permitted(license_name) or info.get('mime') not in ('image/jpeg','image/png'): continue
        if min(info.get('width',0),info.get('height',0))<600: continue
        url=info.get('thumburl') or info.get('url') or ''
        parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.hostname!='upload.wikimedia.org':continue
        try:
            response=session.get(url,timeout=40,stream=True)
            response.raise_for_status()
            buf=bytearray()
            for part in response.iter_content(chunk_size=65536):
                buf.extend(part)
                if len(buf)>12_000_000:raise ValueError('image exceeds size limit')
            img=Image.open(io.BytesIO(buf)).convert('RGB')
            if min(img.size)<500:continue
            p=folder/('photo_%02d.jpg'%(len(output)+1))
            img.save(p,quality=91)
            author=(meta.get('Artist') or {}).get('value','Unknown')
            author=unescape(re.sub('<[^>]*>','',author)).strip()[:200]
            output.append({'file':p.name,'author':author,'license':license_name,
              'source_page':'https://commons.wikimedia.org/wiki/'+quote(page.get('title','').replace(' ','_'),safe=':/_'),
              'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'requires_human_review':True})
            if len(output)>=limit:break
        except Exception as e:
            print('Skip unsuitable Wikimedia file:',str(e)[:100])
    return output

def make_audio(path,duration):
    sr=24000
    t=np.arange(int(sr*duration))/sr
    arr=np.zeros(t.shape,dtype=np.float64)
    chords=[(196,246.94,293.66),(174.61,220,261.63),(164.81,196,246.94),(146.83,185,220)]
    for i,chord in enumerate(chords):
        mask=(t>=duration*i/4)&(t<duration*(i+1)/4)
        x=t[mask]-duration*i/4
        env=(1-np.exp(-x*7))*np.exp(-x*.38)
        for f in chord:arr[mask]+=.023*np.sin(2*np.pi*f*x)*env
    arr*=np.minimum(1,t/.5)*np.minimum(1,(duration-t)/.7)
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr)
        f.writeframes((np.clip(arr,-1,1)*32767).astype('<i2').tobytes())

def fit(image,zoom):
    w,h=SIZE
    ratio=max(w/image.width,h/image.height)*zoom
    img=image.resize((int(image.width*ratio)+2,int(image.height*ratio)+2),Image.Resampling.BICUBIC)
    return ImageOps.fit(img,SIZE,Image.Resampling.BICUBIC)

def render(paths,folder,duration=12.0):
    photos=[Image.open(p).convert('RGB') for p in paths]
    starts=[fit(p,1) for p in photos]
    ends=[fit(p,1.10) for p in photos]
    work=folder/'silent.mp4'
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
         '-s','%dx%d'%SIZE,'-r',str(FPS),'-i','pipe:0','-c:v','libx264',
         '-preset','ultrafast','-crf','22','-pix_fmt','yuv420p',str(work)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    error=None
    try:
        for i in range(int(FPS*duration)):
            t=i/FPS;num=min(len(photos)-1,int(t/duration*len(photos)))
            phase=(t*len(photos)/duration)%1
            frame=Image.blend(starts[num],ends[num],phase)
            if phase>.85 and num<len(photos)-1:
                frame=Image.blend(frame,starts[num+1],min(1,(phase-.85)/.15))
            frame=frame.convert('RGBA')
            shade=Image.new('RGBA',SIZE,(0,0,0,0));d=ImageDraw.Draw(shade)
            d.rectangle((0,0,SIZE[0],105),fill=(8,11,12,150))
            d.text((28,32),'COFFEE / SHORT PR STUDY',
                   font=ImageFont.truetype(FONT,27),fill='white')
            d.rounded_rectangle((20,SIZE[1]-162,SIZE[0]-20,SIZE[1]-24),
                                radius=18,fill=(8,11,12,165))
            lines=['その一杯を、','いつもの休憩に。','コーヒーのある時間。','次のひと休みに。']
            d.text((46,SIZE[1]-140),lines[min(num,3)],
                   font=ImageFont.truetype(FONT,38),fill='white')
            d.text((46,SIZE[1]-75),'DEMO / 架空の店舗・広告ではありません',
                   font=ImageFont.truetype(FONT,17),fill=(245,230,215))
            proc.stdin.write(Image.alpha_composite(frame,shade).convert('RGB').tobytes())
    except Exception as e:error=e
    finally:
        proc.stdin.close()
        msg=proc.stderr.read().decode(errors='replace')
        rc=proc.wait()
    if error:raise error
    if rc:raise RuntimeError('ffmpeg error: '+msg[-500:])
    audio=folder/'audio.wav'
    make_audio(audio,duration)
    final=folder/'preview.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
       '-i',str(work),'-i',str(audio),'-c:v','copy','-c:a','aac',
       '-b:a','96k','-shortest','-movflags','+faststart',str(final)],check=True)
    work.unlink();audio.unlink()
    return final

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',choices=['demo','commons'],default='demo')
    parser.add_argument('--query',default='coffee cafe')
    parser.add_argument('--min-photos',type=int,default=None)
    parser.add_argument('--out',default='output')
    parser.add_argument('--metadata-only',action='store_true')
    args=parser.parse_args()
    folder=Path(args.out);folder.mkdir(parents=True,exist_ok=True)
    photos=folder/'photos';photos.mkdir(exist_ok=True)
    items=demo_photo(photos) if args.source=='demo' else commons_photos(args.query,photos)
    (folder/'sources.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
    minimum=args.min_photos if args.min_photos is not None else (1 if args.source=='demo' else 4)
    if len({x['sha256'] for x in items})<minimum:
        raise SystemExit('SAFETY STOP: insufficient distinct license-tagged photos. No MP4 created.')
    if args.metadata_only:
        print('Validated',len(items),'source images. No MP4 created.');return
    final=render([photos/x['file'] for x in items],folder)
    report={'technical_render_passed':True,'sales_quality_verified':False,
            'publication_authorized':False,'human_review_required':True,
            'source_count':len(items),'additional_charge_jpy':0,
            'generated_utc':datetime.now(timezone.utc).isoformat(),
            'limitation':'Animated still photos, not real motion footage. No business endorsement.'}
    (folder/'quality.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Draft video created:',final)

if __name__=='__main__':main()
