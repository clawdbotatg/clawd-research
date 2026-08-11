# WebRTC, ICE & TURN — and how to make it actually end-to-end encrypted

Research notes, 2026-08-11.

## TLDR

- WebRTC media is **always encrypted on the wire** (DTLS-SRTP is mandatory). ICE/STUN/TURN
  never have the keys — a TURN relay is a blind packet forwarder, so **you don't have to do
  anything special to TURN to get E2EE**.
- For a **1:1 peer-to-peer call**, DTLS-SRTP already *is* end-to-end… except the **signaling
  server can MITM you** by swapping DTLS fingerprints. True E2EE for 1:1 = verify the
  fingerprint/identity out-of-band (SAS code, Signal-style identity keys, etc.).
- The real E2EE problem is **group calls through an SFU**: the SFU terminates DTLS-SRTP and
  sees plaintext. Fix = a **second encryption layer applied to encoded frames in the browser**
  via the Encoded Transform API (`RTCRtpScriptTransform` / insertable streams), ideally using
  the **SFrame** format (RFC 9605), with keys the server never sees — distributed via your own
  secure channel or **MLS** (RFC 9420).

---

## 1. The stack, in one pass

A WebRTC call has three planes:

1. **Signaling** — *not specified by WebRTC*. Your own websocket/HTTP server relays SDP
   offers/answers and ICE candidates. This is the trust-critical plane: whoever runs it can
   try to MITM the call (see §4).
2. **Connectivity: ICE** (Interactive Connectivity Establishment, RFC 8445). Each peer
   gathers *candidates* — ways it might be reachable:
   - **host** candidates: its own local interface addresses;
   - **server-reflexive (srflx)** candidates: its public IP:port as seen by a **STUN** server
     (a trivial "what's my address?" echo service, RFC 8489);
   - **relayed (relay)** candidates: an address allocated on a **TURN** server (RFC 8656)
     that will forward packets on the peer's behalf.
   Both sides exchange candidates over signaling, pair them up, and send STUN connectivity
   checks on every pair; the best working pair wins. TURN is the fallback of last resort
   (~10–20% of real-world connections, symmetric NATs / hostile firewalls).
3. **Transport & media crypto**:
   - One **DTLS handshake** runs over the winning ICE pair. Certificates are self-signed and
     ephemeral; authenticity comes from the **fingerprint carried in the SDP** (`a=fingerprint`).
   - Media (RTP) is encrypted with **SRTP**, keys derived from that DTLS handshake
     (**DTLS-SRTP**, RFC 5763/5764). Data channels run as SCTP directly inside DTLS.
   - Encryption is **mandatory** — there is no unencrypted WebRTC.

### Where TURN sits in the crypto picture

TURN relays the **already-DTLS-encrypted** packets. It knows *who talks to whom, when, and
how much* (metadata), but it cryptographically **cannot** read media — it never participates
in the DTLS handshake. Consequences:

- E2EE requires **zero changes** to STUN/TURN infrastructure. coturn etc. work as-is.
- `turns:` (TURN over TLS, port 443) adds an *outer* TLS layer. That's **not** about media
  secrecy (already covered) — it hides the TURN protocol itself from network middleboxes
  (traversal of DPI firewalls) and hides allocation metadata from a passive network observer.
  Use it for reachability/metadata hygiene, not confidentiality.
- The residual TURN risks are **metadata** (call graph, timing, IP addresses — a hostile TURN
  server learns both parties' IPs) and **availability**. Privacy-hard designs relay *all*
  calls through TURN so the peer never learns your IP (what Signal does when "always relay
  calls" is on), trading latency for IP privacy.

## 2. What you get for free vs. what you don't

| Topology | DTLS-SRTP gives you | E2EE? |
|---|---|---|
| P2P 1:1 (direct or via TURN) | Encryption between the two browsers | **Yes, hop-free** — *if* you defeat the signaling MITM (§4) |
| SFU group call (LiveKit, mediasoup, Jitsi JVB, Janus…) | Encryption browser↔SFU, per hop | **No** — SFU decrypts SRTP, sees every frame |
| MCU / cloud recording / transcoding / SIP gateway | Hop-by-hop only | **No**, structurally — the server must see plaintext to do its job |

An SFU doesn't *transcode* — it just forwards packets selectively — but it still terminates
DTLS-SRTP with each participant, so plaintext frames sit in its memory. "We use WebRTC, it's
encrypted" marketing usually means exactly this hop-by-hop setup.

## 3. E2EE through an SFU: encrypt the frames yourself

The insight: what an SFU needs to route (RTP headers, sequence numbers, simulcast layer /
SVC dependency info, frame boundaries) is **not the media payload**. So encrypt the encoded
frame payload with a key the SFU never has, and leave routing metadata in the clear.

### The browser hook: Encoded Transform

`RTCRtpScriptTransform` (W3C "WebRTC Encoded Transform", the standardized successor of
Chrome's `createEncodedStreams()` insertable-streams experiment) gives you the encoded
frame **after the encoder, before packetization** (and the reverse on receive). You attach a
Worker that transforms each frame:

```js
// main thread
const worker = new Worker('e2ee-worker.js');
sender.transform   = new RTCRtpScriptTransform(worker, { side: 'send' });
receiver.transform = new RTCRtpScriptTransform(worker, { side: 'recv' });

// e2ee-worker.js
onrtctransform = (e) => {
  const { readable, writable } = e.transformer;
  readable
    .pipeThrough(new TransformStream({ transform: encryptOrDecryptFrame }))
    .pipeTo(writable);
};
```

`encryptOrDecryptFrame` does AEAD (AES-GCM / AES-CTR+HMAC) over the frame's payload bytes
using WebCrypto, prepending a small header (key id + counter → nonce). Support is now
universal: Safari shipped it first (15.4), Firefox 117+, and Chrome/Edge support the
standard API alongside their legacy one — Baseline as of late 2025.

### The format: SFrame (RFC 9605, July 2024)

Rather than inventing your own frame format, use **SFrame**: a lightweight AEAD framing for
media frames, purpose-built for exactly this ("the SFU can route but not read"). Per frame:
a header carrying **KID** (key id — which sender/epoch key) and **CTR** (counter → unique
nonce), then ciphertext+tag. Cipher suites: AES-128-CTR+HMAC (short 4/8-byte tags to save
bandwidth on video) or AES-128/256-GCM. It authenticates the sender within the group and is
transport-independent (works over RTP or anything else). Origin: Google Duo shipped an early
version in 2019; the RFC is the IETF-standardized descendant.

Caveats that bite in practice:

- **Codec awareness.** Naively encrypting the whole payload breaks decoders and SFU features
  that peek into the bitstream. Real implementations leave a few unencrypted bytes
  (VP8 payload descriptor equivalent) and/or rely on RTP header extensions like the
  **Dependency Descriptor** so simulcast/SVC layer selection still works with an opaque
  payload. Per-codec packetization rules for SFrame live in AVTCORE work ("SFrame over RTP").
- **Everything server-side that touches media dies**: cloud recording, transcription,
  transcoding, SIP/PSTN bridging, server-side ML. E2EE is a product decision, not a flag.
- **Bandwidth/CPU overhead** is small (per-frame, not per-packet — that's why SFrame beats
  double-SRTP approaches like PERC) but nonzero: header + tag per frame, one AEAD pass in a
  worker.

### Keys: the actual hard part

The crypto layer is easy; **key management is the product**. The server must never see keys,
so you need a key-agreement channel among participants:

- **Shared passphrase** (Jitsi's original demo): everyone derives the same key from a
  password shared out-of-band. Simple, no forward secrecy, no per-sender auth.
- **Per-sender keys over pairwise secure channels**: each participant generates a random
  sender key and sends it to every other participant over an E2E channel (Jitsi uses
  Matrix's **libolm** — Double-Ratchet-style pairwise sessions — as that channel; Signal
  group calls use Signal sessions the same way). Rotate on leave (generate fresh key, resend)
  and **ratchet** on join, so joiners can't read the past and leavers can't read the future.
- **MLS** (Messaging Layer Security, RFC 9420): the scalable answer — tree-based group key
  agreement, O(log n) rekeying, per-epoch group secrets. The IETF SFrame work anticipates
  MLS as the key source: the MLS exporter yields a per-epoch `base_key`, from which
  per-sender SFrame keys are derived; epoch changes map to SFrame KID changes. This is where
  serious implementations are converging (it's also what Discord's DAVE protocol and RCS'
  E2EE adopted for calls/messaging respectively).

### What the frameworks give you today

- **LiveKit**: E2EE built-in at the room level (`e2ee` option + `ExternalKeyProvider`);
  default is a shared key you distribute yourself; per-participant keys / ratcheting /
  MLS-style schemes require implementing a custom key provider. Their docs are explicit that
  the server cannot store or transport keys for you.
- **Jitsi Meet**: production E2EE toggle; per-participant random keys distributed over olm
  channels, AES-GCM frame encryption via insertable streams, automatic rotate-on-leave /
  ratchet-on-join.
- **mediasoup / Janus / medooze**: the SFU is payload-agnostic, so E2EE frames pass through
  fine; medooze published **sframe.js** as a client library. You own the key plane.

## 4. The 1:1 gap everyone forgets: authenticating the DTLS handshake

Even with perfect DTLS-SRTP, the signaling server sees and relays the SDP — including the
`a=fingerprint` that authenticates the DTLS certs. A malicious signaling server can substitute
its own fingerprints and terminate two DTLS sessions (classic MITM), and no browser UI will
tell you. So "P2P WebRTC is E2EE" is only true against everyone *except* your signaling
provider. Closing it requires binding identity to the fingerprint outside the server's reach:

- **Compare fingerprints out-of-band** (read them aloud, QR): crude but sound.
- **SAS** (short authentication string), ZRTP-style: derive a short code from the session
  keys, both users compare verbally.
- **Sign the fingerprint with pre-existing identity keys** (Signal binds call setup to the
  pair's Signal session; Matrix binds it to cross-signed device keys). This is the deployable
  answer when you already have an E2EE messaging layer.
- The old W3C "identity provider" (IdP) hooks in WebRTC never got real adoption — don't build
  on them.

Same story in group calls: SFrame/MLS gives confidentiality against the SFU, but you still
want membership authenticity (who's actually in this epoch?) — MLS handles that; ad-hoc
sender-key schemes need out-of-band verification to resist a server that injects a fake
"participant".

## 5. Threat-model cheat sheet

| Adversary | Defeated by |
|---|---|
| Passive network observer | Stock WebRTC (DTLS-SRTP), nothing to do |
| STUN/TURN operator | Media: nothing to do (never has keys). IP/metadata: `turns:` + always-relay if you care |
| SFU operator / media-server compromise | Frame-layer E2EE: Encoded Transform + SFrame, keys via olm-style channels or MLS |
| Signaling server MITM | Identity binding: OOB fingerprint check, SAS, or signatures with existing identity keys |
| Malicious *client* / endpoint compromise | Out of scope — E2EE ends at the endpoints |
| Metadata analysis (who called whom) | Not solved by any of the above; needs relay/onion designs |

## 6. If building it today (2026)

1. Pick an SFU stack that passes opaque payloads (LiveKit if you want it mostly built;
   mediasoup/medooze if you want control).
2. Frame encryption in a worker via `RTCRtpScriptTransform`, SFrame format (RFC 9605),
   AES-GCM to start.
3. Keys: start with per-sender random keys over an existing E2EE channel with
   rotate-on-leave + ratchet-on-join; graduate to MLS (RFC 9420) if group size/scale demands
   it. Never let keys touch the signaling or media server.
4. Bind identities: sign DTLS fingerprints / SFrame keys with long-term identity keys, or at
   minimum expose an SAS for manual verification.
5. Accept the product cost: no server-side recording/transcription/PSTN on E2EE calls.
6. TURN: deploy coturn with `turns:`; no E2EE-specific work needed.

## Sources

- [RFC 9605 — SFrame](https://www.rfc-editor.org/rfc/rfc9605) · [IETF SFrame WG charter (MLS key derivation intent)](https://datatracker.ietf.org/wg/sframe/about/) · [draft-barnes-sframe-mls](https://datatracker.ietf.org/doc/html/draft-barnes-sframe-mls-00)
- [webrtcHacks — True E2EE with Insertable Streams](https://webrtchacks.com/true-end-to-end-encryption-with-webrtc-insertable-streams/)
- [MDN — Using WebRTC Encoded Transforms](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Using_Encoded_Transforms) · [Firefox intent-to-ship RTCRtpScriptTransform](https://groups.google.com/a/mozilla.org/g/dev-platform/c/Gowr5Fx5jng)
- [LiveKit — E2EE docs](https://docs.livekit.io/home/client/tracks/encryption/) · [LiveKit — encryption overview](https://docs.livekit.io/transport/encryption/)
- [Jitsi — E2EE blog](https://jitsi.org/blog/e2ee/) · [lib-jitsi-meet e2ee.md (olm key distribution, ratcheting)](https://github.com/jitsi/lib-jitsi-meet/blob/master/doc/e2ee.md)
- [Medooze — sframe.js](https://medooze.medium.com/sframe-js-end-to-end-encryption-for-webrtc-f9a83a997d6d) · [Millicast — SFrames with WebRTC](https://medium.com/@millicast/secure-frames-sframes-end-to-end-media-encryption-with-webrtc-98f1506d09eb)
