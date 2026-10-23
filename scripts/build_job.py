"""Build a voiced Reel (or a Story) from a job file. Runs on GitHub Actions.

Job JSON (jobs/<name>.json):
{
  "out": "media/2026-10-23/reel.mp4",
  "type": "reel",                 # or "story" (out should end .jpg)
  "voice": "en-ZA-LukeNeural",    # optional; South African English male voice
  "slides": [
    {"kicker": "Buyer tip", "headline": "Viewing a house this weekend?",
     "body": "3 things most buyers forget to check.",
     "say": "Viewing a house this weekend? Here are three things most buyers forget to check."}
  ]
}
Each slide stays on screen for as long as its voiceover lasts (min 2.5 s).
"""
import asyncio, json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import make_post  # noqa: E402

def dur(path):
    import shutil, re
    if shutil.which("ffprobe"):
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
        return float(out.stdout.strip())
    # no ffprobe (pip static ffmpeg): read "Duration: HH:MM:SS.xx" from ffmpeg's banner
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    h, m, sec = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(sec)

async def _edge(text, voice, path):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate="+5%").save(path)

def tts(text, voice, path):
    """Google's South African English voice (Microsoft's service blocks GitHub runners).
    A voice starting with "edge:" tries Microsoft first."""
    if not str(voice).startswith("edge:"):
        from gtts import gTTS
        gTTS(text, lang="en", tld="co.za").save(path); return
    voice = voice[5:]
    try:
        asyncio.run(asyncio.wait_for(_edge(text, voice, path), 45))
        if os.path.getsize(path) > 1000:
            print("voice: edge", voice, flush=True); return
    except Exception as e:
        print("edge-tts failed:", repr(e), flush=True)
    from gtts import gTTS
    gTTS(text, lang="en", tld="co.za").save(path)
    print("voice: gtts en-ZA", flush=True)

def build(job_path):
    job = json.load(open(job_path))
    make_post.check_wording(job)
    out = job["out"]
    os.makedirs(os.path.dirname(out.rstrip('/')) or '.', exist_ok=True)
    tmp = tempfile.mkdtemp()
    pngs, layers = asyncio.run(make_post.render(job, tmp, layers=True))
    if job.get("type") == "carousel":
        from PIL import Image
        os.makedirs(out, exist_ok=True)
        for i, png in enumerate(pngs, 1):
            Image.open(png).convert("RGB").save(os.path.join(out, f"slide-{i}.jpg"), quality=90)
        return out
    if job.get("type") == "story":
        from PIL import Image
        Image.open(pngs[0]).convert("RGB").save(out, quality=90)
        return out
    voice = job.get("voice", "gtts-za")
    segs = []
    for i, (png, s, (ov, bg)) in enumerate(zip(pngs, job["slides"], layers)):
        say = s.get("say") or " ".join(x for x in (s.get("headline"), s.get("body")) if x)
        mp3 = os.path.join(tmp, f"v{i}.mp3")
        tts(say, voice, mp3)
        tempo = float(job.get("tempo", 1.2))
        d = max(2.2, dur(mp3) / tempo + 0.3)
        seg = os.path.join(tmp, f"s{i}.mp4")
        enc = ["-af", f"atempo={tempo},apad", "-t", f"{d:.2f}", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", seg]
        if bg:  # slow push-in on the photo, text layer fixed on top
            n = int(d * 30) + 2
            zin = i % 2 == 0
            z = f"1+0.08*on/{n}" if zin else f"1.08-0.08*on/{n}"
            fc = (f"[0]scale=2160:3840,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps=30[b];"
                  f"[b][1]overlay=0:0,format=yuv420p[v]")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", bg, "-loop", "1", "-i", ov, "-i", mp3,
                            "-filter_complex", fc, "-map", "[v]", "-map", "2:a"] + enc, check=True)
        else:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", mp3] + enc, check=True)
        segs.append(seg)
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{s}'\n" for s in segs))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", "-movflags", "+faststart", out], check=True)
    return out

if __name__ == "__main__":
    for p in sys.argv[1:]:
        t = json.load(open(p)).get("type")
        if t == "ai_backgrounds":
            import ai_bg
            print("built", ai_bg.build(p))
        elif t == "backgrounds":
            import fetch_bg
            print("built", fetch_bg.build(p))
        elif t == "clip":
            import clip_job
            print("built", clip_job.build(p))
        else:
            print("built", build(p))
