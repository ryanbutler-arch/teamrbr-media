"""Generate photoreal real-estate backgrounds with the free Pollinations (FLUX) image API.
Job: {"type":"ai_backgrounds","out":"brand/backgrounds/ai/<batch>","width":1080,"height":1920,
      "images":{"name":"prompt", ...}}
"""
import json, os, sys, time, urllib.parse, urllib.request
from PIL import Image

STYLE = (", photorealistic professional real estate photography, natural light, high detail, "
         "no people, no text, no watermark, no logos")

def build(job_path):
    job = json.load(open(job_path)); out = job["out"]; os.makedirs(out, exist_ok=True)
    w, h = job.get("width", 1080), job.get("height", 1920); done = []
    for i, (name, prompt) in enumerate(job["images"].items()):
        url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt + STYLE) + "?" +
               urllib.parse.urlencode({"width": w, "height": h, "nologo": "true", "seed": 1000 + i,
                                       "model": "flux", "enhance": "false"}))
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "TeamRBR-media/1.0"})
                data = urllib.request.urlopen(req, timeout=180).read()
                p = os.path.join(out, name + ".jpg"); open(p, "wb").write(data)
                im = Image.open(p).convert("RGB"); im.save(p, quality=88)
                print("saved", name, im.size, flush=True); done.append(name); break
            except Exception as e:
                print("retry", name, attempt, e, flush=True); time.sleep(8)
        time.sleep(3)
    if not done:
        raise SystemExit("no images generated")
    return out

if __name__ == "__main__":
    print("built", build(sys.argv[1]))
