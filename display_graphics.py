# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import gc
import time
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

from adafruit_matrixportal.matrixportal import MatrixPortal
import board

# Colors. Each LED has 3 light states: ON, LOW, HIGH
COLOR_AQUA = 0x00A2FF
COLOR_BLUE = 0x0000AA
COLOR_BLUE_ROYAL = 0x0055FF
COLOR_GREEN = 0x00FF00
COLOR_GREY = 0x555555
COLOR_LIME = 0x55A200
COLOR_LIME_LIGHT = 0x90FF90
COLOR_PINK = 0xFF5555
COLOR_PURPLE = 0x9000FF
COLOR_PURPLE_LIGHT = 0x9090FF
COLOR_WHITE = 0xFFFFFF
COLOR_YELLOW = 0xFFA800

TEMP_COLOR = COLOR_YELLOW
MAIN_COLOR = COLOR_PURPLE_LIGHT  # weather condition
DESCRIPTION_COLOR = COLOR_AQUA
CITY_COLOR = COLOR_PURPLE
HUMIDITY_COLOR = COLOR_BLUE_ROYAL
WIND_COLOR = COLOR_LIME_LIGHT
TIME_COLORS = [COLOR_LIME, COLOR_WHITE, COLOR_GREY]

ICON_WIDTH = 16
ICON_HEIGHT = 16

def _init_fonts(asset_path):
    PATH_FONT_REG_8 = f'{asset_path}/fonts/Roboto-8-Regular.bdf'
    PATH_FONT_MONO_16 = f'{asset_path}/fonts/RobotoMono-16-Semibold.bdf'

    glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: '
    small_font = bitmap_font.load_font(PATH_FONT_REG_8)
    small_font.load_glyphs(glyphs)
    small_font.load_glyphs(('°',))  # a non-ascii character

    clock_font = bitmap_font.load_font(PATH_FONT_MONO_16)
    clock_font.load_glyphs(b'0123456789')

    return (small_font, clock_font)


class DisplayGraphics(displayio.Group):
    def __init__(
            self,
            display,
            logger,
            *,
            am_pm=False,
            celsius=True,
            meters_speed=True,
    ):
        super().__init__()
        self._show_splash(display)

        self.display = display
        self.logger = logger

        # Init units
        self.am_pm = am_pm
        self.celsius = celsius
        self.meters_speed = meters_speed

        self.matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, debug=True)

        # Asset locations
        cwd = ('/' + __file__).rsplit('/', 1)[
            0
        ]  # the current working directory (where this file is)

        # (small_font, clock_font) = _init_fonts(cwd)
        self._init_clock_group(f'{cwd}/fonts/RobotoMono-16-Semibold.bdf')
        # used to short circuit time renders
        self._clock_state = (-1,-1)

    def _init_clock_group(self, clock_font):
        self.matrixportal.add_text(
            text_font=clock_font,
            text_position=(-2, 8),
            text_wrap=3,
            line_spacing=0.6,
            text_color=TIME_COLORS[0],
            scrolling=False,
            is_data=False,
        )
        self.matrixportal.preload_font('1234567890')

    def _show_splash(self, display):
        splash = displayio.Group()

        background = displayio.OnDiskBitmap('loading.bmp')
        bg_sprite = displayio.TileGrid(background, pixel_shader=background.pixel_shader)

        splash.append(bg_sprite)
        display.show(splash)
        gc.collect()

    def update_clock(self, time_tuple):
        hours = time_tuple[3] #+ time_tuple[-1]) % 24
        minutes = time_tuple[4]

        clock_state = (hours, minutes)
        if clock_state == self._clock_state:
            return  # Nothing to do
        self._clock_state = clock_state

        # Change color if not set properly
        if hours < 7:
            time_color = TIME_COLORS[0]
        elif hours < 19:
            time_color = TIME_COLORS[1]
        else:
            time_color = TIME_COLORS[2]
        
        time_str = f'{hours:0>2} {minutes:0>2}'
        self.matrixportal.set_text_color(time_color, 0)
        self.matrixportal.set_text(time_str, 0)

        # self.logger.debug(f'== Display time: {self.hours_label.text}:{self.minutes_label.text}.')
        print(f'== Display time: {time_str}')
        return (hours, minutes)

    def render(self):
        # self.display.show(self.root_group)
        pass
