import hashlib, struct
def der(v):
    b=v.to_bytes(max(1,(v.bit_length()+7)//8),'big')
    return (bytes([0x80|len(b)])+b) if v>=0x80 else b
def f(tag,val):
    if isinstance(val,int): val=val.to_bytes(max(1,(val.bit_length()+7)//8),'big')
    if isinstance(val,str): val=val.encode()
    return der(tag)+der(len(val))+val
def rlp_b(b):
    if len(b)==1 and b[0]<0x80: return b
    return (bytes([0x80+len(b)]) if len(b)<56 else bytes([0xb7+len(der_len(len(b)))])+der_len(len(b)))+b
def der_len(n): return n.to_bytes((n.bit_length()+7)//8,'big')
def rlp_i(i): return rlp_b(b'' if i==0 else i.to_bytes((i.bit_length()+7)//8,'big'))
def rlp_l(items):
    p=b''.join(items)
    return (bytes([0xc0+len(p)]) if len(p)<56 else bytes([0xf7+len(der_len(len(p)))])+der_len(len(p)))+p
usdc=bytes.fromhex("a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
to=bytes.fromhex("d8da6bf26964af9d7eed9e03e53415d37aa96045")
data=bytes.fromhex("a9059cbb")+to.rjust(32,b'\0')+(1000000).to_bytes(32,'big')
tx=b'\x02'+rlp_l([rlp_i(1),rlp_i(0),rlp_i(10**9),rlp_i(30*10**9),rlp_i(60000),rlp_b(usdc),rlp_i(0),rlp_b(data),rlp_l([])])
path=bytes([5])+b''.join(struct.pack(">I",x) for x in [0x8000002c,0x8000003c,0x80000000,0,0])
def dp(elems): return f(0,1)+b''.join(elems)
def value(fam,size,dpath=None,cont=None):
    v=f(0,1)+f(1,fam)+f(2,size)
    if dpath is not None: v+=f(3,dpath)
    if cont is not None: v+=f(4,bytes([cont]))
    return v
# To: RAW address at tuple 0 static leaf
p_to=dp([f(1,struct.pack(">H",0)),f(4,bytes([3]))])
fld_to=f(0,1)+f(1,"To")+f(2,bytes([0]))+f(3,f(0,1)+f(1,value(5,20,p_to)))
p_amt=dp([f(1,struct.pack(">H",1)),f(4,bytes([3]))])
tokamt=f(0,1)+f(1,value(1,32,p_amt))+f(2,value(5,20,cont=1))
fld_amt=f(0,1)+f(1,"Amount")+f(2,bytes([2]))+f(3,tokamt)
h=hashlib.sha3_256(fld_to+fld_amt).digest()
info=f(0,1)+f(1,(1).to_bytes(8,'big'))+f(2,usdc)+f(3,bytes.fromhex("a9059cbb"))+f(4,h)+f(5,"send")+f(6,"Circle")
print("tx",tx.hex(), len(tx))
print("store_apdu","e0040001%02x"%len(path+tx)+(path+tx).hex())
print("fld_to",fld_to.hex(),len(fld_to))
print("fld_amt",fld_amt.hex(),len(fld_amt))
print("fields_hash",h.hex())
print("info_unsigned",info.hex(),len(info))
for n,b in [("to",fld_to),("amt",fld_amt)]:
    pl=len(b).to_bytes(2,'big')+b
    print("apdu_field_"+n,"e0280100%02x"%len(pl)+pl.hex())
