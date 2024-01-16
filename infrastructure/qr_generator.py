# has to be in a separate file so it can be pickled without pulling in django
from multiprocessing import Pool

import qrcode
from more_itertools import chunked
from PIL import Image, ImageDraw, ImageFont, ImageOps


class QRGenerator(object):
    resize_pct = 0.6
    T = 101
    L = 184
    dx = 361
    dy = 340
    
    cols = 4
    rows = 6
    
    def __init__(self, grid):
        self.grid = grid

    def font(self, size):
        # https://fonts.google.com/specimen/Roboto+Condensed
        return ImageFont.truetype("RobotoCondensed-Regular.ttf", size)

    def make_img(self, name, code):
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M
        )
        # TODO: zxing enforces an unnatural decoding scheme
        qr.add_data(code)
        # qr.add_data("".join(map(chr, code)).encode("utf-8"))  # code)
        qr.make()
        q = qr.make_image(fill_color="Black",
                        back_color="white").convert("RGB")
        for_text = 0.2
        im = Image.new("RGB", (q.size[0], int(
            q.size[1] * (1 + for_text))), (255, 255, 255))
        im.paste(q, (0, 0))
        id = ImageDraw.Draw(im)
        ts = im.height / (1 + for_text) * 0.9
        for size in range(100, 1, -3):
            _, _, w, h = id.textbbox((0, 0), name, font=self.font(size))
            text_start = ts + (im.height - ts) / 2 - h / 2
            if w < im.width and text_start + h + im.height * for_text * 0.1 < im.height:
                break
        id.text(
            (im.width // 2 - w // 2, int(text_start)),
            name,
            fill="Black",
            font=self.font(size)
        )
        return im


    def fill_page(self, codes):
        page = self.grid

        for col in range(self.cols):
            for row in range(self.rows):
                t = row*self.cols+col
                if t >= len(codes):
                    return page

                im = self.make_img(*codes[t])
                im = ImageOps.invert(im)
                im = im.resize((round(im.width*self.resize_pct),round(im.height*self.resize_pct)))

                page.paste(im,box=(self.L+self.dx*col, self.T+self.dy*row))
        return page


    def fill_pages(self, codes):
        # https://github.com/Reality-Hack/realityhack.world/raw/4e87c3a49941cb971b3b42113de30ffb50f5bcfb/src/python/grid.png
        M = self.cols * self.rows

        return map(self.fill_page, chunked(codes, M))  # Pool().map(self.fill_page, chunked(codes, M))
