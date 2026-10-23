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
        api = ("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
            "gsrsearch": q + " filetype:bitmap", "gsrlimit": 50, "prop": "imageinfo",
            "iiprop": "url|size|extmetadata", "iiurlheight": 2400}))
        try:
            pages = json.loads(get(api)).get("query", {}).get("pages", {}).values()
        except Exception as e:
            print("search failed", tag, e, flush=True); continue
        results = []
        for pg in pages:
            ii = (pg.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata", {})
            lic = (md.get("LicenseShortName", {}).get("value") or "").lower()
            if not ("cc0" in lic or "public domain" in lic or lic == "pd"): continue
            if ii.get("height", 0) < 1920 or ii.get("width", 0) < 1080: continue
            results.append({"url": ii.get("thumburl") or ii.get("url"), "title": pg.get("title"),
                            "creator": md.get("Artist", {}).get("value"), "license": lic,
                            "foreign_landing_url": ii.get("descriptionurl")})
        print(tag, "usable results:", len(results), flush=True)
        n = 0
        for r in results:
            if n >= job.get("per_query", 6): break
            try:
                data = get(r["url"]); tmp = os.path.join(out, "tmp")
                open(tmp, "wb").write(data)
                im = Image.open(tmp).convert("RGB")
                if im.height < 1920 or im.width < 1080: continue
                im.thumbnail((4000, 2400))
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
