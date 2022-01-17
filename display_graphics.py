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
            matrixportal: MatrixPortal,
            logger,
            *,
            am_pm=False,
            celsius=True,
            meters_speed=True,
    ):
        super().__init__()
        self.matrixportal = matrixportal
        self.logger = logger

        # Init units
        self.am_pm = am_pm
        self.celsius = celsius
        self.meters_speed = meters_speed

        # Asset locations
        # the current working directory (where this file is)
        cwd = ('/' + __file__).rsplit('/', 1)[0]

        # (small_font, clock_font) = _init_fonts(cwd)
        self._init_weather_stats(cwd)
        self._init_clock_group(cwd)
        # used to short circuit time renders
        self._clock_state = (-1,-1)

        # Load the icon sprite sheet
        PATH_WEATHER_ICONS = f'{cwd}/weather-icons.bmp'
        icons = displayio.OnDiskBitmap(PATH_WEATHER_ICONS)
        self._icon_sprite = displayio.TileGrid(
            icons,
            pixel_shader=icons.pixel_shader,
            tile_width=ICON_WIDTH,
            tile_height=ICON_HEIGHT
        )
        self.set_icon(None)

    def set_icon(self, icon_name):
        '''Use icon_name to get the position of the sprite and update
        the current icon.

        :param icon_name: The icon name returned by openweathermap

        Format is always 2 numbers followed by 'd' or 'n' as the 3rd character
        '''

        icon_map = ('01', '02', '03', '04', '09', '10', '11', '13', '50')

        self.logger.debug(f'== Set icon to {icon_name}')
        if self._icon_group:
            self._icon_group.pop()
        if icon_name is not None:
            row = None
            for index, icon in enumerate(icon_map):
                if icon == icon_name[0:2]:
                    row = index
                    break
            column = 0
            if icon_name[2] == 'n':
                column = 1
            if row is not None:
                self._icon_sprite[0] = (row * 2) + column
                self._icon_group.append(self._icon_sprite)

    def _init_clock_group(self, asset_path):
        self.clock_idx = self.matrixportal.add_text(
            text_font=f'{asset_path}/fonts/RobotoMono-16-Semibold.bdf',
            text_position=(-1, 8),
            text_wrap=3,
            line_spacing=0.6,
            text_color=TIME_COLORS[0],
            scrolling=False,
            is_data=False,
        )
        self.matrixportal.preload_font('1234567890', self.clock_idx)

    def _init_weather_stats(self, asset_path):
        small_font = f'{asset_path}/fonts/Roboto-8-Regular.bdf'

        self.temp_idx = self.matrixportal.add_text(
            text_font=small_font,
            text_position=(24 + 16, 0),
            text_anchor_point=(0, 0),
            line_spacing=0.6,
            text_color=TEMP_COLOR,
            scrolling=False,
            is_data=False,
        )
        glyphs = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: °'
        self.matrixportal.preload_font(glyphs, self.temp_idx)

        self.wind_idx = self.matrixportal.add_text(
            text_font=small_font,
            text_position=(24, 17),
            line_spacing=0.6,
            text_color=WIND_COLOR,
            scrolling=False,
            is_data=False,
        )

        self.humidity_idx = self.matrixportal.add_text(
            text_font=small_font,
            text_position=(24, 27),
            line_spacing=0.6,
            text_color=HUMIDITY_COLOR,
            scrolling=False,
            is_data=False,
        )

        self._icon_group = displayio.Group()


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
        self.matrixportal.set_text_color(time_color, self.clock_idx)
        self.matrixportal.set_text(time_str, self.clock_idx)

        # self.logger.debug(f'== Display time: {self.hours_label.text}:{self.minutes_label.text}.')
        print(f'== Display time: {time_str}')
        return (hours, minutes)

    def update_weather(self, weather):
        # set the icon
        # self.set_icon(weather['weather'][0]['icon'])

        city_name = weather['name'] + ', ' + weather['sys']['country']
        temperature = weather['main']['temp']
        temperature = f'{temperature: >2.0f}°C' if self.celsius else  f'{temperature}°F'
        self.matrixportal.set_text(temperature, self.temp_idx)

        description = weather['weather'][0]['description']
        description = description[0].upper() + description[1:]
        # self.description_text.text = description # 'thunderstorm with heavy drizzle'
        self.matrixportal.set_text(description, self.humidity_idx)

        humidity = weather['main']['humidity']
        humidity = f'{humidity}% humidity'
        # self.humidity_label.text = f'{humidity}% humidity'
        self.matrixportal.set_text(humidity, self.humidity_idx)

        wind = round(weather['wind']['speed'])
        if self.meters_speed:
            wind *= 3.6
            wind = f'{wind: <3.1f} km/h'
        else:
            wind = f'{wind} mph'
        self.matrixportal.set_text(wind, self.wind_idx)

        weather_data = [
            temperature,
            description,
            humidity,
            wind,
        ]
        self.logger.debug('== Weather Overview: %s', weather_data)
        gc.collect()
        return True

    def render(self):
        # self.display.show(self.root_group)
        pass
