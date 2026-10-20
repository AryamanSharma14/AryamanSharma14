"""Render an Andrew-style portrait profile in GitHub's native palettes."""
import json
from pathlib import Path
from xml.sax.saxutils import escape

FONT="Consolas,'Liberation Mono',Menlo,monospace"
THEMES={
    'dark':dict(bg='#161b22',text='#c9d1d9',key='#ffa657',value='#a5d6ff',dim='#616e7f'),
    'light':dict(bg='#f6f8fa',text='#1f2328',key='#bc4c00',value='#0a3069',dim='#8c959f'),
}
PORTRAIT=json.loads(Path(__file__).with_name('portrait.json').read_text(encoding='utf-8'))


def text(x,y,value,color,size=16,length=None):
    width=len(value)*size*.6 if length is None else length
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" textLength="{width:.2f}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{escape(value)}</text>' if value else ''


def profile(data,t,mobile=False):
    w,h=(480,1015) if mobile else (985,530)
    px,py,size,step=(67,26,9,9.5) if mobile else (15,27,9,9.5)
    body=''.join(text(px,py+i*step,row.rstrip(),t['text'],size) for i,row in enumerate(PORTRAIT))
    x,y,width=(22,536,436) if mobile else (390,30,570)
    gap=19 if mobile else 20
    body+=text(x,y,'aryaman@github '+ '─'*44,t['text'],13 if mobile else 16,width)
    entries=[
        ('Name','Aryaman Sharma'),('Work','Frappe contributor'),('Focus','Backend · Cloud · CLI'),('OSS','Pilot · Press · Central'),('Languages',' · '.join(name for name,_ in data['langs'][:3])),
        None,('section','Projects'),('Walflow','Local-first background jobs'),('Portscope','Local runtime & port tooling'),
        None,('section','Contact'),('LinkedIn','in/aryamansharma14'),('Portfolio','aryamansharma14.vercel.app'),('Email','aryamansharma4810@gmail.com'),
        None,('section','GitHub Stats / public, all time'),('Pull requests',f'{data["counts"]["opened"]} opened | {data["counts"]["merged"]} merged'),('Frappe PRs',f'{data["counts"]["frappe_opened"]} opened | {data["counts"]["frappe_merged"]} merged'),('Contributions',f'{data["contributions"]:,} in the past year'),
        None,('section','Frappe work'),('Pilot','Processes · builds · security'),('Press / Central','Deployment tooling'),
    ]
    for entry in entries:
        y+=gap
        if entry is None:continue
        key,value=entry
        if key=='section':
            body+=text(x,y,'- '+value+' '+'─'*max(2,57-len(value)),t['text'],13 if mobile else 16,width)
        else:
            prefix='. '+key+':'
            dots='.'*max(2,60-len(prefix)-len(value)-2)
            body+=f'<text x="{x}" y="{y}" font-size="{13 if mobile else 16}" textLength="{width}" lengthAdjust="spacingAndGlyphs" xml:space="preserve"><tspan fill="{t["dim"]}">. </tspan><tspan fill="{t["key"]}">{escape(key)}</tspan><tspan fill="{t["text"]}">:</tspan><tspan fill="{t["dim"]}"> {dots} </tspan><tspan fill="{t["value"]}">{escape(value)}</tspan></text>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}" role="img"><title>Aryaman Sharma — Frappe contributor, backend infrastructure and CLI tooling</title><rect width="{w}" height="{h}" rx="15" fill="{t["bg"]}"/>{body}</svg>'
