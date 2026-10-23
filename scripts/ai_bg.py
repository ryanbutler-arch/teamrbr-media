"""Generate photoreal real-estate backgrounds with free image models.
Order: Hugging Face FLUX.1-schnell Space (anonymous, free GPU quota) -> Pollinations FLUX (anonymous, rate limited).
Job: {"type":"ai_backgrounds","out":"brand/backgrounds/ai/<batch>","images":{"name":"prompt", ...}}
"""
import json, os, shutil, subprocess, sys, time, urllib.parse, urllib.request
from PIL import Image

STYLE = (", photorealistic professional real estate photography, natural light, high detail, "
         "no people, no text, no watermark, no logos")
W, H = 1088, 1920  # full Story/Reel size, no upscaling needed


def hf_client():
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "gradio_client"], check=True, timeout=180)
        from gradio_client import Client
        return Client("black-forest-labs/FLUX.1-schnell")
    except Exception as e:
        print("hf unavailable", repr(e)[:200], flush=True)
        return None


def via_hf(client, prompt, seed, path):
    res = client.predict(prompt=prompt, seed=seed, randomize_seed=False, width=W, height=H,
                         num_inference_steps=4, api_name="/infer")
    src = res[0] if isinstance(res, (list, tuple)) else res
    shutil.copy(src, path)


def via_pollinations(prompt, seed, path):
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) + "?" +
           urllib.parse.urlencode({"width": W, "height": H, "nologo": "true", "seed": seed,
                                   "model": "flux", "referrer": "teamrbr-media"}))
    req = urllib.request.Request(url, headers={"User-Agent": "TeamRBR-media/1.0"})
    open(path, "wb").write(urllib.request.urlopen(req, timeout=180).read())


def build(job_path):
    job = json.load(open(job_path)); out = job["out"]; os.makedirs(out, exist_ok=True)
    client = hf_client(); done = []
    for i, (name, prompt) in enumerate(job["images"].items()):
        p = os.path.join(out, name + ".jpg"); full = prompt + STYLE; seed = 1000 + i
        for how in ("hf",):  # Pollinations dropped: its free tier returns ~576px images (too soft)
            try:
                if how == "hf":
                    if not client: continue
                    via_hf(client, full, seed, p)
                else:
                    via_pollinations(full, seed, p)
                im = Image.open(p).convert("RGB")
                if im.width < 1000 or im.height < 1800:
                    raise ValueError(f"too small {im.size}")
                im.save(p, quality=92)
                print("saved", name, how, im.size, flush=True); done.append(name); break
            except Exception as e:
                print("fail", name, how, repr(e)[:200], flush=True)
                if os.path.exists(p): os.remove(p)
                if how == "hf" and "quota" in str(e).lower(): client = None
                time.sleep(20 if how == "poll" else 2)
        time.sleep(4)
    if not done:
        raise SystemExit("no images generated")
    return out

if __name__ == "__main__":
    print("built", build(sys.argv[1]))
