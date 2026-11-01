"""Serve the render page and pipe POSTed rgb48 HLG frames into ffmpeg.
Usage: python3 serve.py WEDGIE_DEV_PUBLIC NODE_MODULES_PARENT OUT_DIR [W H FPS]"""
import http.server, subprocess, sys, os, threading

pub, nm, out = sys.argv[1], sys.argv[2], sys.argv[3]
W, H, FPS = (int(x) for x in (sys.argv[4:7] if len(sys.argv) > 6 else (1920, 1080, 60)))
here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(out, exist_ok=True)
ff = None

class H_(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        p = path.split("?")[0]
        if p.startswith("/wd/"): return os.path.join(pub, p[4:])
        if p.startswith("/node_modules/"): return os.path.join(nm, p[1:])
        return os.path.join(here, p.lstrip("/") or "index.html")
    def log_message(self, *a): pass
    def do_POST(self):
        global ff
        n = int(self.headers.get("Content-Length", 0)); body = self.rfile.read(n)
        if self.path == "/frame":
            if ff is None:
                ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb48le",
                    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "ffv1", "-pix_fmt", "gbrp16le",
                    f"{out}/master.mkv"], stdin=subprocess.PIPE)
            ff.stdin.write(body)
        elif self.path == "/done" and ff:
            ff.stdin.close(); ff.wait(); ff = None
            threading.Thread(target=srv.shutdown).start()
        self.send_response(204); self.end_headers()

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8931), H_)
print("serving on 8931", flush=True)
srv.serve_forever()
