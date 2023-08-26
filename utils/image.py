from PIL import Image, ImageSequence, ImageDraw
from io import BytesIO 


AV_WIDTH = 205 
AV_CORNER = (93, 34)
LVL_CORNER = (329, 142)
LVL_HEIGHT = 229 - 142

numbers = {}
for i in range(9):
    im = Image.open(f'assets/{i}.png')
    newy = LVL_HEIGHT 
    newx = round(im.size[0] * (newy / im.size[1]))
    im = im.resize((newx, newy))
    numbers[str(i)] = im 

frames = []
gif = Image.open('assets/rc.gif')
for frame in ImageSequence.Iterator(gif):
    frames.append(frame)


def generate_rank_card(level, av_data):
    save_kwargs = {
        "format": "GIF",
        "save_all": True
    }

    layer = Image.new(mode='RGBA', size=frames[0].size, color=(0, 0, 0, 0))
    
    av = Image.open(BytesIO(av_data))
    av = av.resize((AV_WIDTH, AV_WIDTH)) 
    mask = Image.new("L", av.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([(0, 0), av.size], fill=255)
    layer.paste(av, AV_CORNER, mask)

    digitx = LVL_CORNER[0]
    digity = LVL_CORNER[1]

    for digit in str(level):
        im = numbers[digit]
        layer.paste(im, (digitx, digity))
        digitx += im.size[0]

    for frame in frames:
        frame = frame.copy()
        frame.paste(layer)
        frames.append(frame)

    byteframes = []
    for f in frames:
        byte = BytesIO()
        byteframes.append(byte)
        f.save(byte, format='GIF')
    imgs = [Image.open(byteframe) for byteframe in byteframes]

    out = BytesIO()
    imgs[1].save(out, append_images=imgs[2:], **save_kwargs)
    out.seek(0)
    return out 

