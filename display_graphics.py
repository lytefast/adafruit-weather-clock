# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

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

cwd = ('/' + __file__).rsplit('/', 1)[
    0
]  # the current working directory (where this file is)

PATH_FONT_REG_8 = f'{cwd}/fonts/Roboto-8-Regular.bdf'
PATH_FONT_MONO_16 = f'{cwd}/fonts/RobotoMono-16-Semibold.bdf'

PATH_WEATHER_ICONS = f'{cwd}/weather-icons.bmp'
ICON_WIDTH = 16
ICON_HEIGHT = 16


class Display_Graphics(displayio.Group):
    def __init__(
            self,
            display,
            logger,
            *,
            am_pm=False,
            units='metric'
    ):
        super().__init__()
        self._show_splash(display)

        self.display = display
        self.logger = logger

        # Init units
        self.am_pm = am_pm
        if units == 'imperial':
            self.celsius = False
            self.meters_speed = False
        else:
            self.celsius = True
            self.meters_speed = True

        # Setup display
        self.root_group = displayio.Group()
        self.root_group.append(self)

        small_font = self._init_fonts()
        self._init_weather_stats(small_font)
        self._init_clock_group()
        # used to short circuit time renders
        self._clock_state = (-1,-1)

        self._text_group = displayio.Group()
        self.append(self._text_group)

        # Load the icon sprite sheet
        icons = displayio.OnDiskBitmap(PATH_WEATHER_ICONS)
        self._icon_sprite = displayio.TileGrid(
            icons,
            pixel_shader=icons.pixel_shader,
            tile_width=ICON_WIDTH,
            tile_height=ICON_HEIGHT
        )

        self.set_icon(None)
        self._scrolling_texts = []

    def _init_fonts(self):
        glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: '
        small_font = bitmap_font.load_font(PATH_FONT_REG_8)
        small_font.load_glyphs(glyphs)
        small_font.load_glyphs(('°',))  # a non-ascii character

        return small_font

    def _init_weather_stats(self, small_font):

        self.temp_label = Label(small_font)
        self.temp_label.color = TEMP_COLOR
        self.wind_label = Label(small_font)
        self.wind_label.color = WIND_COLOR
        self.humidity_label = Label(small_font)
        self.humidity_label.color = HUMIDITY_COLOR
        # self.description_text = Label(small_font)
        # self.description_text.color = DESCRIPTION_COLOR
        self._icon_group = displayio.Group()

        weather_group = displayio.Group()
        weather_group.append(self._icon_group)
        weather_group.append(self.temp_label)
        weather_group.append(self.wind_label)
        weather_group.append(self.humidity_label)
        weather_group.x = 24

        self.temp_label.x = 16
        self.temp_label.y = 6
        self.wind_label.y = 18
        self.humidity_label.y = 27

        self.append(weather_group)

    def _init_clock_group(self):
        clock_font = bitmap_font.load_font(PATH_FONT_MONO_16)
        clock_font.load_glyphs(b'0123456789')

        self.hours_label = Label(clock_font)
        self.hours_label.color = TIME_COLORS[0]
        self.minutes_label = Label(clock_font)
        self.minutes_label.color = TIME_COLORS[0]

        clock_group = displayio.Group()
        clock_group.append(self.hours_label)
        clock_group.append(self.minutes_label)
        clock_group.x = -2

        self.hours_label.y = 5
        # set minutes to bottom half of screen
        self.minutes_label.y = 22

        self.clock_group = clock_group
        self.append(clock_group)

    def _show_splash(self, display):
        splash = displayio.Group()

        background = displayio.OnDiskBitmap('loading.bmp')
        bg_sprite = displayio.TileGrid(background, pixel_shader=background.pixel_shader)

        splash.append(bg_sprite)
        display.show(splash)

    def display_weather(self, weather):
        # set the icon
        self.set_icon(weather['weather'][0]['icon'])

        city_name = weather['name'] + ', ' + weather['sys']['country']

        temperature = weather['main']['temp']
        if self.celsius:
            self.temp_label.text = f'{temperature: >2.0f}°C'
        else:
            self.temp_label.text = f'{temperature: >2.0f}°F'

        # description = weather['weather'][0]['description']
        # description = description[0].upper() + description[1:]
        # self.description_text.text = description # 'thunderstorm with heavy drizzle'

        humidity = weather['main']['humidity']
        self.humidity_label.text = f'{humidity}% humidity'

        wind = round(weather['wind']['speed'])
        if self.meters_speed:
            wind *= 3.6
            self.wind_label.text = f'{wind: <3.1f} km/h'
        else:
            self.wind_label.text = f'{wind} mph'

        weather_data = [
            self.temp_label.text,
            # self.description_text.text,
            self.humidity_label.text,
            self.wind_label.text,
        ]
        self.logger.debug('== Weather Overview: %s', weather_data)
        self.display.show(self.root_group)

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
    
    def display_clock(self, time_tuple):
        hours = time_tuple[3] #+ time_tuple[-1]) % 24
        minutes = time_tuple[4]

        clock_state = (hours, minutes)
        if clock_state == self._clock_state:
            return  # Nothing to do
        self._clock_state = clock_state

        self.hours_label.text = f'{hours:0>2}'
        self.minutes_label.text = f'{minutes:0>2}'

        # Change color if not set properly
        if hours < 7:
            time_color = TIME_COLORS[0]
        elif hours < 19:
            time_color = TIME_COLORS[1]
        else:
            time_color = TIME_COLORS[2]
        
        self.hours_label.color = time_color
        self.minutes_label.color = time_color

        self.logger.debug(f'== Display time: {self.hours_label.text}:{self.minutes_label.text}. {time_tuple}')
        self.display.show(self.root_group)
        return (hours, minutes)

    def render(self):
        self.display.show(self.root_group)
