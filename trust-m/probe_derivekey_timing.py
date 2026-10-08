import optiga, time
OID = 0xF1DA
o = optiga.Chip()
orig = o.read(OID)
sec = lambda: o.read(0xE0C5)[0]
def derive(seed, n=32):
    d = b"\x01\x00\x02" + OID.to_bytes(2, "big") + b"\x03\x00\x02" + n.to_bytes(2, "big")
    d += b"\x02" + len(seed).to_bytes(2, "big") + seed + b"\x07\x00\x00"
    return o.command(0x34, 0x01, d)
try:
    o.write(OID, bytes(range(1, 33)), erase=True)
    o.set_metadata(OID, {0xE8: b"\x21", 0xD3: b"\x00", 0xD1: b"\xFF"})
    print("SEC before", sec())
    ts = []
    for i in range(40):
        t = time.ticks_ms(); derive(b"wots-index-" + ("%05d" % i).encode()); ts.append(time.ticks_diff(time.ticks_ms(), t))
    print("SEC after 40", sec(), "ms", ts[:5], "...", ts[-5:])
    t = time.ticks_ms(); r = derive(b"wots-index-big..", 256); print("256B derive ms", time.ticks_diff(time.ticks_ms(), t), len(r))
    t = time.ticks_ms(); r = derive(b"wots-index-min..", 16); print("16B derive ms", time.ticks_diff(time.ticks_ms(), t), len(r))
    t = time.ticks_ms(); o.sha256(b"x" * 64); print("sha256 ms", time.ticks_diff(time.ticks_ms(), t))
    print("SEC end", sec())
finally:
    o.set_metadata(OID, {0xD1: b"\x00", 0xE8: b"\x00", 0xD3: b"\xFF"})
    o.write(OID, orig, erase=True)
    print("restored", "zero" if not any(o.read(OID)) else "DIRTY")
