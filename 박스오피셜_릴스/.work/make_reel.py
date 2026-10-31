import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

SP = "/home/user/claude-code-mastery/박스오피셜_릴스"
REF = SP + "/.work/ref"
FONT = SP + "/.work/fonts/Pretendard-{}.otf"
W, H = 1080, 1920
GREEN, YELLOW = (63, 212, 124), (255, 226, 77)

photo_path, slug, credit = sys.argv[1], sys.argv[2], sys.argv[3]
l1, l2, l3 = sys.argv[4], sys.argv[5], sys.argv[6]
clip = sys.argv[7] if len(sys.argv) > 7 else None  # optional news clip shown over the photo
VY = int(os.environ.get("VY", "250"))  # top of the clip on the canvas

canvas = Image.new("RGB", (W, H), "black")

# photo fills the top, fading to black where the title starts
ph = Image.open(photo_path).convert("RGB")
# cover at least 1000px of height so a landscape photo still reaches the title;
# FOCUSX (0-1) picks which part of a wide photo stays in frame
scale = max(W / ph.width, 1000 / ph.height)
ph = ph.resize((round(ph.width * scale), round(ph.height * scale)), Image.LANCZOS)
fx = float(os.environ.get("FOCUSX", "0.5"))
left = min(max(round(ph.width * fx - W / 2), 0), ph.width - W)
ph = ph.crop((left, 0, left + W, min(ph.height, 1100)))
if clip:
    # the photo becomes a quiet backdrop so the clip reads first
    ph = ImageEnhance.Brightness(ph.filter(ImageFilter.GaussianBlur(18))).enhance(0.45)
mask = Image.new("L", ph.size, 255)
md = ImageDraw.Draw(mask)
fade_from = ph.height - 380
for y in range(fade_from, ph.height):
    md.line([(0, y), (W, y)], fill=round(255 * (1 - (y - fade_from) / 380) ** 1.4))
canvas.paste(ph, (0, 0), mask)
d = ImageDraw.Draw(canvas)

TRACK = -0.045  # letter spacing as a share of font size; Pretendard runs wide at display sizes

def tlen(text, f):
    return d.textlength(text, font=f) + TRACK * f.size * (len(text) - 1)

def tdraw(xy, text, f, fill):
    # PIL has no letter-spacing, so place each glyph and pull the next one in
    x, y = xy
    for i, ch in enumerate(text):
        d.text((x, y), ch, font=f, fill=fill, anchor="ls")
        x += d.textlength(text[:i + 1], font=f) - d.textlength(text[:i], font=f) + TRACK * f.size

def fit(text, weight, size, maxw):
    while True:
        f = ImageFont.truetype(FONT.format(weight), size)
        if tlen(text, f) <= maxw or size <= 40:
            return f
        size -= 2

# credit badge, top right
cf = ImageFont.truetype(FONT.format("SemiBold"), 24)
tw = d.textlength(credit, font=cf)
x1 = W - 44; x0 = x1 - tw - 24
d.rounded_rectangle([x0, 40, x1, 78], 6, fill=(30, 30, 30))
d.text((x0 + 12, 59), credit, font=cf, fill="white", anchor="lm")

# channel tag
tf = ImageFont.truetype(FONT.format("Bold"), 34)
tdraw((76, 934), "[박스오피셜]", tf, "white")

# two green lines, one yellow box line
f1 = fit(l1, "ExtraBold", 92, 950); f2 = fit(l2, "ExtraBold", 92, 950)
size = min(f1.size, f2.size)
fg = ImageFont.truetype(FONT.format("ExtraBold"), size)
tdraw((66, 1052), l1, fg, GREEN)
tdraw((66, 1167), l2, fg, GREEN)
f3 = fit(l3, "ExtraBold", 74, 880)
w3 = tlen(l3, f3)
d.rounded_rectangle([64, 1208, 64 + w3 + 40, 1306], 6, fill=YELLOW)
tdraw((84, 1284), l3, f3, "black")

# logo, cut from an existing title screen so it matches the channel exactly
ref = Image.open(REF + "/kg2_f1.png").convert("RGB")
canvas.paste(ref.crop((380, 1340, 700, 1520)), (380, 1340))

out1 = f"{SP}/out/{slug}_f1.png"
bg = f"{SP}/out/{slug}_bg.png"
canvas.save(bg if clip else out1)

# screen 2: the channel promo card, taken from the reference reel
end = f"{SP}/out/end.png"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "6", "-i", REF + "/kg2_video.mp4", "-frames:v", "1", end], check=True)

video = f"{SP}/out/{slug}_video.mp4"
if clip:
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", clip]).decode())
    # poster: the title screen with a frame from the clip in place
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", bg, "-ss", "3", "-i", clip,
                    "-filter_complex", f"[1]scale={W}:-2[c];[0][c]overlay=0:{VY}", "-frames:v", "1", out1], check=True)
    off = dur - 0.4
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-loop", "1", "-t", f"{dur}", "-i", bg,
        "-i", clip,
        "-loop", "1", "-t", "3.6", "-i", end,
        "-filter_complex",
        f"[1:v]scale={W}:-2,fps=30[c];[0:v]fps=30[b];[b][c]overlay=0:{VY}:shortest=1,format=yuv420p[s1];"
        f"[2:v]fps=30,format=yuv420p[s2];[s1][s2]xfade=transition=fade:duration=0.4:offset={off:.3f},format=yuv420p[v];"
        f"[1:a]afade=t=out:st={off:.3f}:d=0.4,apad=whole_dur={off + 3.6:.3f}[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-c:a", "aac", "-b:a", "160k",
        "-t", f"{off + 3.6:.3f}", "-movflags", "+faststart", video], check=True)
    print(out1, video)
    sys.exit()
subprocess.run([
    "ffmpeg", "-v", "error", "-y",
    "-loop", "1", "-t", "4.4", "-i", out1,
    "-loop", "1", "-t", "3.6", "-i", end,
    "-f", "lavfi", "-t", "7.6", "-i", "anullsrc=r=44100:cl=stereo",
    "-filter_complex", "[0][1]xfade=transition=fade:duration=0.4:offset=4,format=yuv420p,fps=30[v]",
    "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-c:a", "aac", "-shortest",
    "-movflags", "+faststart", video], check=True)
print(out1, video)
