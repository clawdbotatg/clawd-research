import json,sys
t=open(sys.argv[1]).read()
t=t[t.index('{'):t.rindex('}')+1]
d=json.loads(t)
print(d.keys())
NP=[56,57,56,60,60,63,64,63,60,66,60,65,70,60,64,68]
def cnt(x): return sum(cnt(y) for y in x) if isinstance(x,list) else 1
tot={}
for i in range(16):
    t_=i+2
    c={k:cnt(d[k][i]) for k in d}
    tot[t_]=sum(c.values())
    print(t_, c, tot[t_], tot[t_]*32)
print('all',sum(tot.values())*32,'t<=7',sum(v for k,v in tot.items() if k<=7)*32)
for k in [2,4,5,6,7]: pass
