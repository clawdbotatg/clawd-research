#!/usr/bin/env python3
"""Camera -> Bonsai 2 vision loop test.
Grabs a frame with ~/vision/vision.py, sends it to the local Bonsai server, times every stage,
and scores yes/no facts. Usage: ./vision_test.py desk1 desk2 [--runs N] [--effort medium] [--scale 1.0] [--no-capture]
"""
import argparse, base64, json, os, subprocess, sys, time, urllib.request

VISION = os.path.expanduser("~/vision")
URL = f"http://127.0.0.1:{os.environ.get('BONSAI_PORT','8090')}/v1/chat/completions"

DESCRIBE = ("This is a frame from a home security camera. In 2-3 plain sentences, say what you see: "
            "the room or surface, main objects, lighting (day, night/infrared, dark), and whether any people are visible.")

# yes/no facts to grade against. Fill in truth per camera once you've looked at the frame yourself.
FACTS = {
    "desk1": [("Is the image in color?", False), ("Is it a dark or night-vision image?", True),
              ("Is a person clearly visible?", False), ("Is there a cardboard box visible?", False)],
    "desk2": [("Is the image in color?", True), ("Is it a dark or night-vision image?", False),
              ("Is a person clearly visible?", False), ("Is there a cardboard box or package with a label visible?", True),
              ("Is there a cable or wire crossing the foreground?", True)],
}

def capture(cam):
    t = time.time()
    r = subprocess.run([f"{VISION}/vision.py", "look", cam], cwd=VISION, capture_output=True, text=True, timeout=60)
    ok = "FAILED" not in r.stdout and "STALE" not in r.stdout
    return f"{VISION}/frames/{cam}.jpg", time.time() - t, ok, r.stdout.strip().splitlines()[-1]

def ask(img_b64, text, effort, max_tokens=400, think=True):
    body = {"messages": [{"role": "user", "content": [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + img_b64}}]}],
        "max_tokens": max_tokens, "chat_template_kwargs": {"reasoning_effort": effort, "enable_thinking": think}}
    t = time.time()
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=600))
    wall = time.time() - t
    m = r["choices"][0]["message"]; tm = r.get("timings", {})
    return m.get("content", "").strip(), len(m.get("reasoning_content") or ""), tm, wall

def load(path, scale):
    if scale == 1.0:
        return base64.b64encode(open(path, "rb").read()).decode()
    out = path + ".scaled.jpg"
    subprocess.run(["sips", "-Z", str(int(640 * scale)), path, "--out", out], capture_output=True, check=True)
    return base64.b64encode(open(out, "rb").read()).decode()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cams", nargs="+"); ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--effort", default="medium"); ap.add_argument("--think", default="on", choices=["on","off"]); ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--no-capture", action="store_true"); ap.add_argument("--json", help="append results here")
    a = ap.parse_args()
    for cam in a.cams:
        for run in range(a.runs):
            if a.no_capture:
                path, cap_s, ok, note = f"{VISION}/frames/{cam}.jpg", 0.0, True, "cached frame"
            else:
                path, cap_s, ok, note = capture(cam)
            if not ok:
                print(f"[{cam}] capture failed: {note}"); continue
            b64 = load(path, a.scale)
            desc, rlen, tm, desc_s = ask(b64, DESCRIBE, a.effort, think=(a.think == "on"))
            # graded facts, one yes/no per call, no reasoning
            score = []; fact_s = 0.0
            for q, truth in FACTS.get(cam, []):
                ans, _, tmq, w = ask(b64, q + " Answer only yes or no.", "medium", 8, think=False)
                fact_s += w; got = ans.lower().startswith("yes")
                score.append((q, truth, got, got == truth))
            n_ok = sum(1 for s in score if s[3])
            print(f"\n=== {cam} run {run+1}  think={a.think} effort={a.effort} scale={a.scale} ===")
            print(f"capture {cap_s:.1f}s | describe {desc_s:.1f}s (prompt {tm.get('prompt_n',0)} tok @ {tm.get('prompt_per_second',0):.0f}/s, "
                  f"gen {tm.get('predicted_n',0)} tok @ {tm.get('predicted_per_second',0):.1f}/s, reasoning {rlen} chars) | "
                  f"{len(score)} facts {fact_s:.1f}s | TOTAL loop {cap_s+desc_s:.1f}s")
            print("BONSAI:", desc)
            for q, truth, got, hit in score:
                print(f"  {'OK ' if hit else 'MISS'} {q}  truth={truth} got={got}")
            print(f"facts: {n_ok}/{len(score)}")
            if a.json:
                with open(a.json, "a") as f:
                    f.write(json.dumps({"cam": cam, "run": run, "effort": a.effort, "think": a.think, "scale": a.scale, "capture_s": cap_s,
                                        "describe_s": desc_s, "timings": tm, "reasoning_chars": rlen, "desc": desc,
                                        "facts": n_ok, "facts_n": len(score), "facts_s": fact_s}) + "\n")

if __name__ == "__main__":
    main()
