#!/usr/bin/env python3
"""Run the 5 real transcripts from clawd-harness bench_naming.py through the
fine-tuned model — eyeball check that it didn't just memorize synthetic style."""
import json
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
from gen_data import SYS

SAMPLES = [
    "User: add a swipe-to-dismiss gesture to the photo gallery\nClaude: I'll add "
    "touchstart/touchend handlers tracking horizontal delta and animate off-screen.",
    "User: the deploy keeps failing on vercel with a 404 on the api routes\nClaude: "
    "Usually a rewrites/output-dir mismatch — let me check vercel.json and the preset.",
    "User: refactor the auth middleware to use JWT refresh tokens\nClaude: I'll split "
    "access/refresh, add a rotation endpoint and httpOnly cookies.",
    "User: set up a github action to run pytest on every PR\nClaude: I'll add a "
    "workflow with a matrix over python versions and a pip cache.",
    "User: can you write a haiku about debugging\nClaude: Sure — here's one about the "
    "late-night hunt for a null pointer.",
]

model, tokenizer = load("mlx-community/Qwen3-0.6B-bf16", adapter_path="adapters")
sampler = make_sampler(temp=0.0)
for s in SAMPLES:
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": s}]
    prompt = tokenizer.apply_chat_template(msgs, add_generation_prompt=True,
                                           enable_thinking=False)
    out = generate(model, tokenizer, prompt=prompt, max_tokens=120,
                   sampler=sampler, verbose=False)
    print(out)
