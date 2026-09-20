# Bonsai 2 looks at the house cameras

Test: `vision_test.py` grabs a frame with `~/vision/vision.py look <cam>`, sends it to the local
Bonsai server, times each stage, then asks yes/no facts (thinking off, 8 tokens) and grades them
against what I saw in the frame myself. Run 2026-09-19, frames 640x360 from desk1 (night IR,
blurry) and desk2 (color, cable across lens, box with label). floater1 was down (hub 5XX), iPad cast stale.

```
./vision_test.py desk1 desk2                # capture + describe with thinking
./vision_test.py desk1 desk2 --think off    # fast mode
./vision_test.py desk2 --no-capture --scale 0.5 --json out.jsonl
```

## Speed

| mode | image prefill | describe | facts (per yes/no) | whole loop |
|---|---|---|---|---|
| think on, 640x360, cold | 280 tok, ~2.5 s | 14–26 s | 0.4–0.9 s | 15–27 s |
| think off, 640x360 | (cached) | 4.6–8.8 s | 0.4 s | ~5–9 s |
| think off, 320x180 | 122 tok, ~2 s | 6–7 s | 0.4 s | ~7 s |

Capture is 0.4–0.6 s. The server caches image tokens, so repeat questions about the same frame
skip prefill. Gen ran 11–26 tok/s across the session; the low end was machine load (Chrome + another
Python at 100%), text-only dropped the same way.

## Accuracy

| frame | think on | think off | think off, half size |
|---|---|---|---|
| desk1 (night IR) | 4/4 | 4/4, 3/4 | 3/4 |
| desk2 (color, box, cable) | 5/5 | 5/5, 5/5 | 4/5 |

Descriptions were right every time: called desk1 dark infrared, out of focus, object too close
to lens, no people. Called desk2 a cluttered desk, teal-and-white box with barcode, coiled cable
in the foreground, indoor light, no people. It read the Reolink logo, camera label and timestamp.
The misses were the "is it dark/night-vision" yes/no flipping on desk1 with thinking off, and
"is it color" once at half size. Thinking on is more consistent but 3x slower.

## Takeaways

- **Loop floor is ~5 s** per frame with thinking off. That's a "what's on the desk now" check, not
  a live feed.
- **Yes/no questions are 0.4 s** once the frame is in cache. Cheap to ask many per frame.
- **Quality is fine** for room-level facts. Half-size frames save little and cost accuracy; stay at 640x360.
- **Grader gotcha:** short answers with thinking on end up in `reasoning_content`, content is empty.
  Pass `"enable_thinking": false` for yes/no.
- Next: a person-present alarm (one yes/no per second per cam) or "what changed since 10 min ago"
  with two frames.
