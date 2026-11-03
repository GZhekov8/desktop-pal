import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math, random
R=ROOT + '/itch/raw/'; O=ROOT + '/itch/'
def font(sz, bold=False):
    for f in (['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if bold else ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']):
        try: return ImageFont.truetype(f, sz)
        except: pass
    return ImageFont.load_default()
def wallpaper(w, h, c1, c2, seed=1):
    random.seed(seed)
    img = Image.new('RGB', (w, h)); px = img.load()
    for y in range(h):
        for x in range(0, w):
            t = (x / w * .6 + y / h * .4)
            px[x, y] = tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))
    blobs = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(blobs)
    for _ in range(7):
        r = random.randint(120, 320); x = random.randint(-100, w); y = random.randint(-100, h)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, random.randint(14, 30)))
    blobs = blobs.filter(ImageFilter.GaussianBlur(60))
    return Image.alpha_composite(img.convert('RGBA'), blobs)
def window(img, box, title):
    x0, y0, x1, y1 = box
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((x0 + 6, y0 + 10, x1 + 6, y1 + 14), 12, fill=(0, 0, 0, 70))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, 12, fill=(250, 250, 252, 255))
    d.rounded_rectangle((x0, y0, x1, y0 + 38), 12, fill=(236, 238, 242, 255)); d.rectangle((x0, y0 + 26, x1, y0 + 38), fill=(236, 238, 242, 255))
    d.text((x0 + 16, y0 + 11), title, fill=(90, 96, 108), font=font(14))
    for i, c in enumerate([(230, 230, 233), (230, 230, 233), (230, 230, 233)]):
        d.rectangle((x1 - 30 - i * 30, y0 + 15, x1 - 20 - i * 30, y0 + 17), fill=(150, 150, 160))
    random.seed(x0)
    y = y0 + 64
    d.rounded_rectangle((x0 + 28, y, x0 + 28 + (x1 - x0) * .45, y + 14), 4, fill=(60, 64, 72)); y += 36
    while y < y1 - 30:
        ln = random.uniform(.5, .92) * (x1 - x0 - 56)
        d.rounded_rectangle((x0 + 28, y, x0 + 28 + ln, y + 8), 4, fill=(210, 213, 220)); y += random.choice([20, 20, 20, 36])
def taskbar(img):
    w, h = img.size; d = ImageDraw.Draw(img)
    bar = Image.new('RGBA', (w, 44), (24, 28, 36, 215)); img.alpha_composite(bar, (0, h - 44))
    ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    cols = [(110, 168, 230), (240, 190, 90), (120, 200, 150), (220, 120, 120), (170, 150, 230)]
    for i in range(5): od.rounded_rectangle((w / 2 - 110 + i * 46, h - 35, w / 2 - 84 + i * 46, h - 9), 6, fill=cols[i] + (200,))
    img.alpha_composite(ov)
    d.text((w - 70, h - 30), '14:35', fill=(235, 238, 245), font=font(14))
    pw = Image.open(ROOT + '/src/assets/tray.png').convert('RGBA').resize((18, 18))
    img.alpha_composite(pw, (w - 104, h - 31))
def shot(name, pet, wp, title):
    img = wallpaper(1280, 720, *wp)
    window(img, (90, 70, 860, 600), title)
    taskbar(img)
    p = Image.open(R + pet).convert('RGBA'); p = p.resize((int(p.width * .56), int(p.height * .56)), Image.LANCZOS)
    img.alpha_composite(p, (1280 - p.width - 14, 720 - 44 - p.height))
    img.convert('RGB').save(O + name, quality=92)
shot('screenshot-1-otter.png', 'otter-water.png', ((86, 126, 168), (40, 66, 104)), 'Notes — Project plan')
shot('screenshot-2-cat.png', 'cat-bill.png', ((122, 98, 150), (52, 48, 92)), 'Budget.xlsx')
shot('screenshot-3-fox.png', 'fox-peek.png', ((70, 120, 110), (30, 62, 66)), 'Inbox')
shot('screenshot-4-dog.png', 'dog-mom.png', ((168, 120, 92), (88, 58, 52)), 'Weekend plans')
shot('screenshot-5-redpanda.png', 'panda-sleepy.png', ((44, 52, 84), (18, 22, 40)), 'Late night reading')
shot('screenshot-6-todos.png', 'otter-nudge.png', ((96, 140, 150), (44, 74, 96)), 'Report draft')
# app window shots on a soft background
for n, src in (('screenshot-7-app.png', 'app-list.png'), ('screenshot-8-new-reminder.png', 'app-form.png')):
    img = wallpaper(1280, 720, (230, 214, 196), (196, 170, 150), 3)
    a = Image.open(R + src).convert('RGBA'); a = a.resize((int(a.width * .58), int(a.height * .58)), Image.LANCZOS)
    x, y = (1280 - a.width) // 2, (720 - a.height) // 2
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((x + 8, y + 14, x + a.width + 8, y + a.height + 18), 14, fill=(60, 30, 10, 90))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    mask = Image.new('L', a.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, a.width, a.height), 12, fill=255)
    img.paste(a, (x, y), mask)
    img.convert('RGB').save(O + n, quality=92)
# cover 630x500
cv = wallpaper(630, 500, (246, 214, 176), (226, 150, 104), 7)
d = ImageDraw.Draw(cv)
d.text((315, 52), 'Desktop Pal', fill=(74, 40, 22), font=font(54, True), anchor='mm')
d.text((315, 102), 'A little pet in the corner of your screen', fill=(110, 62, 34), font=font(20), anchor='mm')
d.text((315, 128), 'that reminds you to do things', fill=(110, 62, 34), font=font(20), anchor='mm')
rows = [(['n-cat.png', 'n-redpanda.png'], 168), (['n-fox.png', 'n-otter.png', 'n-dog.png'], 318)]
for files, y in rows:
    ims = [Image.open(R + f).convert('RGBA') for f in files]
    ims = [im.resize((int(im.width * .27), int(im.height * .27)), Image.LANCZOS) for im in ims]
    gap = 6; total = sum(im.width for im in ims) + gap * (len(ims) - 1); x = (630 - total) // 2
    for im in ims: cv.alpha_composite(im, (x, y)); x += im.width + gap
cv.convert('RGB').save(O + 'cover-630x500.png')
print('done')
