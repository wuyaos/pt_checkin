from __future__ import annotations

from PIL import ImageChops, Image

RGB_BLACK = (0, 0, 0)


class DmhyImageProcessor:
    def __init__(self, image: Image.Image):
        self.image = image
        self.width, self.height = image.size

    def compare_images_sort(self, another_image: Image.Image) -> bool:
        if self.image.size != another_image.size:
            return False
        point1 = self.get_split_point()
        point2 = DmhyImageProcessor(another_image).get_split_point()
        return bool(point1 and point1 == point2)

    def check_analysis(self) -> bool:
        pixel_points = [
            (0, self.height - 1), (1, self.height - 2), (self.width - 1, 0),
            (self.width - 2, 1), (self.width - 1, self.height - 1),
            (self.width - 2, self.height - 2)
        ]
        return any(
            self.image.getpixel(point) == RGB_BLACK for point in pixel_points
        )

    def remove_date_string(self):
        p = Image.new('RGB', (276, 15), (0, 0, 0))
        self.image.paste(p, (2, self.height - 32))

    def compare_with(
            self, another_image: Image.Image
    ) -> tuple[Image.Image, Image.Image, Image.Image] | None:
        image_a_compare = self.image.crop(
            (0, 0, self.width, self.height - 45))
        b_width, b_height = another_image.size
        image_b_compare = another_image.crop(
            (0, 0, b_width, b_height - 45))

        diff = ImageChops.difference(image_a_compare, image_b_compare)
        if diff.getbbox() is None:
            return None
        return self.image, another_image, diff

    def get_split_point(self) -> tuple[int, int] | None:
        blank_in_bottom_left = (
                self.image.getpixel((0, self.height - 1)) == RGB_BLACK and
                self.image.getpixel((1, self.height - 2)) == RGB_BLACK)
        blank_in_top_right = (
                self.image.getpixel((self.width - 1, 0)) == RGB_BLACK and
                self.image.getpixel((self.width - 2, 1)) == RGB_BLACK)

        x, y = 0, 0
        if blank_in_bottom_left:
            for w in range(1, self.width):
                pixel = self.image.getpixel((w, self.height - 1))
                if isinstance(pixel, tuple) and (
                        pixel[0] > 7 or pixel[1] > 7 or pixel[2] > 7):
                    x = w
                    break
        elif blank_in_top_right:
            for h in range(1, self.height):
                pixel = self.image.getpixel((self.width - 1, h))
                if isinstance(pixel, tuple) and (
                        pixel[0] > 7 or pixel[1] > 7 or pixel[2] > 7):
                    y = h
                    break
        return (x, y) if x > 100 or y > 100 else None

    def split_image(self) -> tuple[Image.Image, Image.Image] | None:
        split_point = self.get_split_point()
        if not split_point:
            return None
        
        x, y = split_point
        if x > 0:
            a1 = self.image.crop((0, 0, x, self.height))
            a2 = self.image.crop((x, 0, self.width, self.height))
        else:
            a1 = self.image.crop((0, 0, self.width, y))
            a2 = self.image.crop((0, y, self.width, self.height))
        return a1, a2

