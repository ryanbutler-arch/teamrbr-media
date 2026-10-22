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
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())

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
    pngs = asyncio.run(make_post.render(job, tmp))
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
    for i, (png, s) in enumerate(zip(pngs, job["slides"])):
        say = s.get("say") or " ".join(x for x in (s.get("headline"), s.get("body")) if x)
        mp3 = os.path.join(tmp, f"v{i}.mp3")
        tts(say, voice, mp3)
        tempo = float(job.get("tempo", 1.2))
        d = max(2.2, dur(mp3) / tempo + 0.3)
        seg = os.path.join(tmp, f"s{i}.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", mp3,
                        "-af", f"atempo={tempo},apad", "-t", f"{d:.2f}", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", seg], check=True)
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
