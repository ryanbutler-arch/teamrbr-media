"""Turn one of Ryan's raw phone clips into a finished Reel (runs on GitHub Actions).

Job JSON: {"type":"clip","source":"<Drive share/download link or any https URL>",
           "out":"media/YYYY-MM-DD/clip.mp4",
           "endcard":{"kicker":"Team RBR","headline":"Want the checklist?","body":"...","cta":"Comment MARKET"},
           "max_seconds":90}
Steps: download -> fit to 1080x1920 -> transcribe (faster-whisper) -> burn word-timed captions
-> append a 3 s branded end card -> H.264/AAC, faststart.
"""
import asyncio, json, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import make_post  # noqa: E402

def run(*a):
    subprocess.run(list(a), check=True)

def download(src, dst):
    m = re.search(r"(?:id=|/d/)([A-Za-z0-9_-]{20,})", src)
    if "drive.google" in src and m:
        import gdown
        gdown.download(id=m.group(1), output=dst, quiet=True)
    else:
        import urllib.request
        urllib.request.urlretrieve(src, dst)
    if not os.path.exists(dst) or os.path.getsize(dst) < 10000:
        raise SystemExit("download failed or file too small: " + src)

def ts(t):
    h, r = divmod(max(t, 0), 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"

def captions(video, ass_path, max_s):
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", video, "-f", "s16le", "-ac", "1",
                          "-ar", "16000", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    segs, _ = model.transcribe(audio, language="en", word_timestamps=True, vad_filter=True)
    words = [w for s in segs for w in (s.words or []) if w.start < max_s]
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 4 or w.word.strip().endswith((".", "?", "!", ",")):
            lines.append(cur); cur = []
    if cur: lines.append(cur)
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Montserrat ExtraBold,78,&H00FFFFFF,&H00FFFFFF,&H002B2B2B,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,2,70,70,560,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for ln in lines:
        text = " ".join(w.word.strip() for w in ln).upper()
        text = text.replace("{", "(").replace("}", ")")
        ev.append(f"Dialogue: 0,{ts(ln[0].start)},{ts(ln[-1].end + 0.05)},Cap,,0,0,0,,{text}")
    open(ass_path, "w").write(head + "\n".join(ev) + "\n")
    print("caption lines:", len(ev), flush=True)

def build(job_path):
    job = json.load(open(job_path))
    make_post.check_wording(job.get("endcard", {}))
    out = job["out"]; os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = tempfile.mkdtemp(); max_s = float(job.get("max_seconds", 90))
    raw = os.path.join(tmp, "raw"); download(job["source"], raw)
    fit = os.path.join(tmp, "fit.mp4")
    run("ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-t", str(max_s),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x2B2B2B,fps=30,format=yuv420p",
        "-c:v", "libx264", "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", fit)
    ass = os.path.join(tmp, "cap.ass"); captions(fit, ass, max_s)
    capd = os.path.join(tmp, "cap.mp4")
    run("ffmpeg", "-y", "-loglevel", "error", "-i", fit, "-vf", f"ass={ass}",
        "-c:v", "libx264", "-crf", "21", "-c:a", "copy", capd)
    parts = [capd]
    if job.get("endcard"):
        pngs = asyncio.run(make_post.render({"type": "story", "slides": [job["endcard"]]}, tmp))
        endv = os.path.join(tmp, "end.mp4")
        run("ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", pngs[0], "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo", "-t", "3", "-r", "30", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", endv)
        parts.append(endv)
    lst = os.path.join(tmp, "l.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    run("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
        "-c:v", "libx264", "-crf", "22", "-c:a", "aac", "-movflags", "+faststart", out)
    return out

if __name__ == "__main__":
    print("built", build(sys.argv[1]))
