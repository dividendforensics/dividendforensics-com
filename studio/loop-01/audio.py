import math, random, struct, wave
SR=44100; T=8.0; N=int(SR*T); random.seed(7)
L=[0.0]*N
def add(i,v):
    if 0<=i<N: L[i]+=v
for k in range(int(T*2)):                      # kick on every beat (120 BPM)
    s=int(k*0.5*SR); ph=0.0
    for j in range(int(0.35*SR)):
        t=j/SR; f=45+90*math.exp(-t*28); ph+=2*math.pi*f/SR
        add(s+j,0.9*math.sin(ph)*math.exp(-t*9))
for k in range(int(T*2)):                      # off-beat hat
    s=int((k*0.5+0.25)*SR)
    for j in range(int(0.06*SR)):
        add(s+j,(random.random()*2-1)*0.18*math.exp(-j/SR*70))
for j in range(N):                             # bass drone, whole cycles per loop => seamless
    t=j/SR; L[j]+=0.18*math.sin(2*math.pi*55*t)+0.07*math.sin(2*math.pi*110.5*t*1.0)
pk=max(abs(x) for x in L); 
with wave.open('audio.wav','wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<hh',int(x/pk*0.89*32767),int(x/pk*0.89*32767)) for x in L))
print('audio ok')
