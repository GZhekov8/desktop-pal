import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import random, math
random.seed(11)
def bez(p0,p1,p2,p3,t):
    u=1-t
    return tuple(u**3*a+3*u*u*t*b+3*u*t*t*c+t**3*d for a,b,c,d in zip(p0,p1,p2,p3))
segs=[((52,115),(58,99),(84,90),(116,88)),((116,88),(140,86),(162,85),(178,90)),((178,90),(192,93),(206,103),(205,120))]
top=[]
for s in segs:
    for i in range(80): top.append(bez(*s,i/80))
def topy(x):
    c=[p for p in top if abs(p[0]-x)<1.2]
    return min(p[1] for p in c) if c else None
def hexmix(a,b,t):
    a=[int(a[i:i+2],16) for i in (1,3,5)]; b=[int(b[i:i+2],16) for i in (1,3,5)]
    return '#%02x%02x%02x'%tuple(round(x+(y-x)*t) for x,y in zip(a,b))
buckets={}
def add(color,op,w,d):
    k=(color,op,w); buckets.setdefault(k,[]).append(d)
def q(v,n=8): return round(v*n)/n
def strand(x,y,ang,ln,curl):
    ex,ey=x+math.cos(ang)*ln,y+math.sin(ang)*ln
    cx,cy=(x+ex)/2+math.cos(ang+1.57)*curl,(y+ey)/2+math.sin(ang+1.57)*curl
    return f"M{x:.1f} {y:.1f}Q{cx:.1f} {cy:.1f} {ex:.1f} {ey:.1f}"
# palette buckets (quantised so paths can be merged)
def bodycol(depth,chest):
    base=hexmix('#8c6044','#2a170d',min(1,depth))
    return hexmix(base,'#b99a78',chest)
out=[]
# ---- body interior strands
for _ in range(1500):
    x=random.uniform(56,205); ty=topy(x)
    if ty is None: continue
    y=random.uniform(ty+0.8,125)
    depth=(y-ty)/30
    chest=min(1,max(0,(x-150)/38))*max(0,1-depth*1.6)
    col=bodycol(round(depth*6)/6,round(chest*4)/4)
    ang=math.pi+0.25+random.gauss(0,.25)  # fur lies toward the tail
    ln=random.uniform(2.2,4.5)
    op=random.choice([.45,.65,.85]); w=random.choice([.45,.6])
    add(col,op,w,strand(x,y,ang,ln,random.uniform(-.8,.8)))
# ---- highlights on top surface (light from above)
for _ in range(380):
    x=random.uniform(62,182); ty=topy(x)
    if ty is None: continue
    y=ty+random.uniform(0.5,5)
    chest=max(0,(x-150)/38)
    col=hexmix('#b3825d','#e4cfb0',round(chest*3)/3)
    add(col,random.choice([.35,.55]),.45,strand(x,y,math.pi+.3+random.gauss(0,.3),random.uniform(1.8,3.6),random.uniform(-.6,.6)))
# ---- silhouette tufts along the back (wet, clumped)
for i in range(0,len(top),2):
    x,y=top[i]
    if x<56 or x>204: continue
    ang=-math.pi/2+random.gauss(0,.35)-0.35
    ln=random.uniform(1.4,3.4)
    add(hexmix('#7a5137','#c0a07c',min(1,max(0,(x-150)/38))),.8,.55,strand(x,y+1,ang,ln,random.uniform(-1,1)))
# ---- tail strands
for _ in range(260):
    x=random.uniform(14,58); half=2.5+ (x-14)/44*3.5
    y=random.uniform(115.5-half,118+half*0.4)
    add(hexmix('#6a4430','#2a170d',round(random.random()*3)/3),random.choice([.55,.8]),.5,strand(x,y,math.pi+random.gauss(0,.25),random.uniform(2,4),random.uniform(-.6,.6)))
# ---- wet spiky clumps at the waterline
for _ in range(90):
    x=random.uniform(54,204); y=random.uniform(118,124)
    add('#24140b',.8,.7,strand(x,y,math.pi/2*random.choice([-1,1])*0.15-math.pi/2*0.1+math.pi+random.gauss(0,.4),random.uniform(2,4),0))
body=''.join(f'<path d="{"".join(v)}" stroke="{k[0]}" stroke-opacity="{k[1]}" stroke-width="{k[2]}"/>' for k,v in buckets.items())

# ---- head strands (local coords of head group)
buckets.clear()
for _ in range(900):
    a=random.uniform(0,2*math.pi); r=math.sqrt(random.uniform(0,1))
    x=27*r*math.cos(a); y=-1+21*r*math.sin(a)
    if -16<x<16 and -9<y<14 and abs(x)<14 and random.random()<.6: continue  # keep the face clean
    rr=math.hypot(x/27,(y+1)/21)
    col=hexmix('#f2e8d6','#8a6a4c',round(min(1,max(0,rr-.45)*1.9)*5)/5)
    ang=math.atan2(y-3,x)+random.gauss(0,.35)
    ln=1.4+rr*2.6
    add(col,random.choice([.5,.75]),.45,strand(x,y,ang,ln,random.uniform(-.5,.5)))
for i in range(160):  # fluffy outline
    a=2*math.pi*i/160; x=27*math.cos(a); y=-1+21*math.sin(a)
    if y>12: continue
    col='#d8c4a2' if y<-4 else '#a7896a'
    add(col,.75,.5,strand(x,y,a+random.gauss(0,.3),random.uniform(1.2,2.8),random.uniform(-.6,.6)))
head=''.join(f'<path d="{"".join(v)}" stroke="{k[0]}" stroke-opacity="{k[1]}" stroke-width="{k[2]}"/>' for k,v in buckets.items())
open(ROOT + '/tools/body_fur.svgfrag','w').write(f'<g class="furstrands" fill="none" stroke-linecap="round">{body}</g>')
open(ROOT + '/tools/head_fur.svgfrag','w').write(f'<g class="furstrands" fill="none" stroke-linecap="round">{head}</g>')
print(len(body),len(head))
