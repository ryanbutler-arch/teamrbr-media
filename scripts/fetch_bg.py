"""Collect free-to-use (CC0 / public domain) real estate photos from Openverse into brand/backgrounds/candidates.
Job: {"type":"backgrounds","out":"brand/backgrounds/candidates/<batch>","queries":{"tag":"search words",...},"per_query":6}
"""
import json, os, sys, time, urllib.parse, urllib.request
from PIL import Image

UA = {"User-Agent": "TeamRBR-media/1.0 (ryan.butler@kwsa.co.za)"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()

def build(job_path):
    job = json.load(open(job_path)); out = job["out"]; os.makedirs(out, exist_ok=True)
    meta = []
    for tag, q in job["queries"].items():
        api = ("https://api.openverse.org/v1/images/?" + urllib.parse.urlencode(
            {"q": q, "license": "cc0,pdm", "size": "large", "page_size": 30, "mature": "false"}))
        try:
            results = json.loads(get(api)).get("results", [])
        except Exception as e:
            print("search failed", tag, e, flush=True); continue
        n = 0
        for r in results:
            if n >= job.get("per_query", 6): break
            try:
                data = get(r["url"]); tmp = os.path.join(out, "tmp")
                open(tmp, "wb").write(data)
                im = Image.open(tmp).convert("RGB")
                if min(im.size) < 900: continue
                im.thumbnail((1600, 1600))
                name = f"{tag}-{n+1}.jpg"; im.save(os.path.join(out, name), quality=85)
                meta.append({"file": name, "tag": tag, "title": r.get("title"), "creator": r.get("creator"),
                             "license": r.get("license"), "source": r.get("foreign_landing_url")})
                n += 1; print("saved", name, flush=True)
            except Exception as e:
                print("skip", e, flush=True)
            time.sleep(0.5)
        if os.path.exists(os.path.join(out, "tmp")): os.remove(os.path.join(out, "tmp"))
    json.dump(meta, open(os.path.join(out, "sources.json"), "w"), indent=1)
    return out

if __name__ == "__main__":
    print("built", build(sys.argv[1]))
