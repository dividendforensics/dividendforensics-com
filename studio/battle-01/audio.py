import json,math,random,struct,wave
SR=44100;d=json.load(open('events.json'));T=d['dur']+0.2;N=int(SR*T);L=[0.0]*N;random.seed(1)
def tone(t0,f,dur,amp,decay,shape='sin'):
    s=int(t0*SR)
    for j in range(int(dur*SR)):
        if s+j>=N:break
        t=j/SR;e=math.exp(-t*decay)
        v=math.sin(2*math.pi*f*t) if shape=='sin' else (random.random()*2-1)
        L[s+j]+=amp*v*e
PENT=[261.6,293.7,329.6,392.0,440.0,523.3,587.3,659.3]
last={'bounce':-1,'clack':-1}
for e in d['events']:
    t=e['t'];k=e['type']
    if k=='bounce' and t-last['bounce']>0.05 and e.get('v',0)>200:
        tone(t,random.choice(PENT),0.25,0.35,14);last['bounce']=t
    elif k=='clack' and t-last['clack']>0.04:
        tone(t,1800,0.04,0.25,90,'noise');last['clack']=t
    elif k=='hit': tone(t,110,0.3,0.7,10);tone(t,2500,0.08,0.3,60,'noise')
    elif k=='die':
        for i,f in enumerate([392,329.6,261.6]): tone(t+i*0.12,f,0.25,0.5,12)
    elif k=='win':
        for i,f in enumerate([523.3,659.3,784,1046.5]): tone(t+i*0.13,f,0.8,0.5,4)
for j in range(N): L[j]+=0.06*math.sin(2*math.pi*55*(j/SR))   # low bed
pk=max(abs(x) for x in L) or 1
with wave.open('audio.wav','wb') as w:
    w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<hh',int(x/pk*0.9*32767),int(x/pk*0.9*32767)) for x in L))
print('audio',round(T,2))
