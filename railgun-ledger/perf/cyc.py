import sys,re,collections
txt=open(sys.argv[1]).read(); core=sys.argv[2]
for fn in ['mont16','mont32']:
  m=re.search(r'<%s>:\n(.*?)(\n\n|\Z)'%fn,txt,re.S)
  ins=[l.split('\t')[2].split('.')[0] for l in m.group(1).splitlines() if l.count('\t')>=2]
  c=collections.Counter(ins)
  cyc=0
  for k,v in c.items():
    if core=='m0':
      if k in('ldr','str','ldrh','strh','ldrb','strb'):w=2
      elif k in('push','pop','ldmia','stmia','ldm','stm'):w=4  # rough
      elif k.startswith('b') and k not in('bics',):w=2
      else:w=1
    else:
      if k.startswith('ldr') or k.startswith('str'):w=1.5
      elif k in('push','pop','ldmia','stmia','ldm','stm','strd','ldrd'):w=3
      elif k.startswith('b') and k not in('bic','bics','bfi'):w=2
      else:w=1
    cyc+=v*w
  print(fn,len(ins),'instrs, est cycles',cyc, c.most_common(12))
