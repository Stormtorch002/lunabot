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


frame1 = Image.open('assets/frame1.png').convert(mode='RGBA')
frame2 = Image.open('assets/frame2.png').convert(mode='RGBA')

def generate_rank_card(level, av_file):
    save_kwargs = {
        "format": "GIF",
        "save_all": True, 
        "loop": 0,
        "duration": 1000
    }

    layer = Image.new(mode='RGBA', size=frame1.size, color=(0, 0, 0, 0))

    with Image.open(av_file) as av:
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

    f1 = frame1.copy()
    f2 = frame2.copy()

    f1.paste(layer, (0, 0), layer)
    f2.paste(layer, (0, 0), layer)

    out = BytesIO()
    f1.save(out, append_images=[f2], **save_kwargs)
    # layer.save(out, 'png')
    out.seek(0)
    return out 

