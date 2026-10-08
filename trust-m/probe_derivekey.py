import optiga, ubinascii
h = lambda b: ubinascii.hexlify(b).decode()
OID = 0xF1DA
o = optiga.Chip()
orig = o.read(OID)
def derive(seed, n=32):
    d = b"\x01\x00\x02" + OID.to_bytes(2, "big")          # secret object
    d += b"\x03\x00\x02" + n.to_bytes(2, "big")           # output length
    d += b"\x02" + len(seed).to_bytes(2, "big") + seed    # label+seed
    d += b"\x07\x00\x00"                                   # export to host
    return o.command(0x34, 0x01, d)                        # 0x01 = TLS1.2 PRF SHA256
def step(name, f):
    try:
        r = f(); print("OK  ", name, h(r) if isinstance(r, bytes) else r)
    except Exception as e:
        print("FAIL", name, repr(e), getattr(e, "code", ""))
secret = bytes(range(1, 33))   # test secret, not a real key
try:
    step("write secret", lambda: o.write(OID, secret, erase=True))
    step("type=PRESSEC", lambda: o.set_metadata(OID, {0xE8: b"\x21", 0xD3: b"\x00"}))
    step("derive (read open)", lambda: derive(b"wots-index-0007"))
    step("read=NEV", lambda: o.set_metadata(OID, {0xD1: b"\xFF"}))
    step("read secret (should fail)", lambda: o.read(OID))
    step("derive (read locked)", lambda: derive(b"wots-index-0007"))
    step("derive idx 8", lambda: derive(b"wots-index-0008"))
    print("META", {hex(k): h(v) for k, v in o.metadata(OID).items()})
finally:
    step("restore read=ALW,type=BSTR", lambda: o.set_metadata(OID, {0xD1: b"\x00", 0xE8: b"\x00", 0xD3: b"\xFF"}))
    step("restore data", lambda: o.write(OID, orig, erase=True))
    print("AFTER", {hex(k): h(v) for k, v in o.metadata(OID).items()}, "zero" if not any(o.read(OID)) else "DIRTY")
