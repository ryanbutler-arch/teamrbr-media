"""Team RBR self-built Instagram media (backup when Canva fails or runs out).

Usage:
  python3 scripts/make_post.py spec.json OUTDIR

spec.json:
{
  "type": "story" | "reel",
  "slides": [
    {"kicker": "Buyer tip", "headline": "Viewing a house this weekend?",
     "body": "Here are 3 things most buyers forget to check.", "cta": "DM me 'CHECK'"}
  ],
  "seconds_per_slide": 3          (reel only, optional)
}

Output: OUTDIR/story.jpg (story) or OUTDIR/reel.mp4 (reel), 1080x1920.
Branding: Montserrat, KW red #B40101, charcoal #2B2B2B, white footer with the
official KW Eden logo (brand/kw-eden-logo.png). Text is HTML-escaped.

Setup in a fresh workspace (once per run):
  npm install --prefix /tmp/rbrfonts @fontsource/montserrat@5.1.0
"""
import asyncio, base64, html, json, os, subprocess, sys
from playwright.async_api import async_playwright

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = "/tmp/rbrfonts/node_modules/@fontsource/montserrat/files"
LOGO = os.path.join(REPO, "brand", "kw-eden-logo.png")
FOOTER = ("Ryan Butler", "Team RBR", "083 281 7918")
BANNED = ("realty", "valuation")


def b64(path, mime):
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def css():
    faces = "".join(
        f"@font-face{{font-family:M;src:url({b64(f'{FONT_DIR}/montserrat-latin-{w}-normal.woff2','font/woff2')});font-weight:{w}}}"
        for w in (400, 700, 800)
    )
    return faces + """
*{margin:0;box-sizing:border-box}
body{width:1080px;height:1920px;font-family:M;background:#2B2B2B;color:#fff;display:flex;flex-direction:column;
justify-content:center;padding:120px 96px 330px;position:relative;overflow:hidden}
.bar{position:absolute;top:0;left:0;right:0;height:24px;background:#B40101}
.kick{color:#B40101;font-weight:800;font-size:40px;letter-spacing:6px;text-transform:uppercase;margin-bottom:40px}
h1{font-weight:800;font-size:112px;line-height:1.03}
p{font-size:50px;line-height:1.35;margin-top:52px;color:#e6e6e6}
.cta{display:inline-block;margin-top:68px;background:#B40101;padding:34px 54px;font-weight:800;font-size:52px}
.foot{position:absolute;bottom:0;left:0;right:0;height:230px;background:#fff;display:flex;align-items:center;
justify-content:space-between;padding:0 72px;color:#2B2B2B;font-size:27px;font-weight:700;line-height:1.5}
.foot img{height:120px}
"""


def slide_html(s, style, logo):
    e = lambda k: html.escape(s.get(k) or "")
    cta = f"<div><span class=cta>{e('cta')}</span></div>" if s.get("cta") else ""
    body = f"<p>{e('body')}</p>" if s.get("body") else ""
    kick = f"<div class=kick>{e('kicker')}</div>" if s.get("kicker") else ""
    foot = "<br>".join(html.escape(x) for x in FOOTER)
    return (f"<html><head><meta charset=utf-8><style>{style}</style></head><body><div class=bar></div>"
            f"{kick}<h1>{e('headline')}</h1>{body}{cta}<div class=foot><div>{foot}</div><img src='{logo}'></div></body></html>")


def check_wording(spec):
    text = json.dumps(spec).lower()
    hits = [w for w in BANNED if w in text]
    if hits:
        sys.exit(f"Blocked words in copy: {hits}")


async def render(spec, out):
    style, logo = css(), b64(LOGO, "image/png")
    paths = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        for i, s in enumerate(spec["slides"]):
            await pg.set_content(slide_html(s, style, logo))
            await pg.evaluate("document.fonts.ready")
            path = os.path.join(out, f"slide{i}.png")
            await pg.screenshot(path=path)
            paths.append(path)
        await b.close()
    return paths


def to_reel(paths, out, secs):
    fade = 0.5
    args = ["ffmpeg", "-y", "-loglevel", "error"]
    for pth in paths:
        args += ["-loop", "1", "-t", str(secs), "-i", pth]
    if len(paths) == 1:
        fc = "[0]format=yuv420p[v]"
    else:
        parts, prev = [], "[0]"
        for i in range(1, len(paths)):
            label = f"[x{i}]"
            parts.append(f"{prev}[{i}]xfade=transition=fade:duration={fade}:offset={i*(secs-fade):.2f}{label}")
            prev = label
        fc = ";".join(parts) + f";{prev}format=yuv420p[v]"
    dst = os.path.join(out, "reel.mp4")
    subprocess.run(args + ["-filter_complex", fc, "-map", "[v]", "-r", "30", "-c:v", "libx264",
                           "-crf", "22", "-movflags", "+faststart", dst], check=True)
    return dst


def main():
    spec = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    check_wording(spec)
    paths = asyncio.run(render(spec, out))
    if spec.get("type") == "reel":
        print(to_reel(paths, out, float(spec.get("seconds_per_slide", 3))))
    else:
        from PIL import Image
        dst = os.path.join(out, "story.jpg")
        Image.open(paths[0]).convert("RGB").save(dst, quality=90)
        print(dst)


if __name__ == "__main__":
    main()
