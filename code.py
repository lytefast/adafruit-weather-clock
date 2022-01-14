# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Matrix Weather display
# For Metro M4 Airlift with RGB Matrix shield, 64 x 32 RGB LED Matrix display

"""
This example queries the Open Weather Maps site API to find out the current
weather for your location... and display it on a screen!
if you can find something that spits out JSON data, we can display it
"""
import time
import board
import microcontroller
import adafruit_logging as logging
import display_graphics
import traceback

from digitalio import DigitalInOut, Direction, Pull
from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix
from aio_handler import AIOHandler


ONE_MIN = 60
ONE_HOUR = 60 * ONE_MIN

TIME_SYNC_INTERVAL = ONE_HOUR
WEATHER_SYNC_INTERVAL = 15 * ONE_MIN

SCROLL_HOLD_TIME = 0.2  # set this to hold each line before finishing scroll

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print('== WiFi secrets are kept in secrets.py, please add them there!')
    raise

network = Network(status_neopixel=board.NEOPIXEL, debug=True)

logger = logging.getLogger('aio')
logger.addHandler(AIOHandler('adafruit-weather-clock', network))
logger.setLevel(logging.WARNING)
logger.critical('== Initializing adafruit-weather-clock ====')

if hasattr(board, 'D12'):
    jumper = DigitalInOut(board.D12)
    jumper.direction = Direction.INPUT
    jumper.pull = Pull.UP
    is_metric = jumper.value
elif hasattr(board, 'BUTTON_DOWN') and hasattr(board, 'BUTTON_UP'):
    logger.debug(f'== Button DOWN/UP found')

    button_down = DigitalInOut(board.BUTTON_DOWN)
    button_down.switch_to_input(pull=Pull.UP)

    button_up = DigitalInOut(board.BUTTON_UP)
    button_up.switch_to_input(pull=Pull.UP)
    if not button_down.value:
        logger.debug('== Down Button Pressed')
        microcontroller.nvm[0] = 1
    elif not button_up.value:
        logger.debug('== Up Button Pressed')
        microcontroller.nvm[0] = 0
    is_metric = microcontroller.nvm[0]
else:
    is_metric = True

if is_metric:
    UNITS = 'metric'  # can pick 'imperial' or 'metric' as part of URL query
else:
    UNITS = 'imperial'
logger.info(f'== Jumper set to {UNITS}')

# # Use cityname, country code where countrycode is ISO3166 format.
# # E.g. "New York, US" or "London, GB"
# LOCATION = "Oakland, CA, US"
# DATA_SOURCE = (
#     f'https://api.openweathermap.org/data/2.5/weather?q='
#     f'{LOCATION}'
#     f'&units={UNITS}'
#     f'&appid={secrets["openweather_token"]}'
# )
DATA_SOURCE = (
    f'https://api.openweathermap.org/data/2.5/weather'
    f'?lat={secrets["latitude"]}'
    f'&lon={secrets["longitude"]}'
    f'&units={UNITS}'
    f'&appid={secrets["openweather_token"]}'
)
DATA_LOCATION = []
SCROLL_HOLD_TIME = 0.2  # set this to hold each line before finishing scroll

# --- Display setup ---
matrix = Matrix()
if UNITS in ('imperial', 'metric'):
    gfx = display_graphics.Display_Graphics(
        matrix.display, logger,
        am_pm=False, units=UNITS
    )

class Context:
    localtime_refresh_ts = -TIME_SYNC_INTERVAL - 1
    weather_refresh_ts = -WEATHER_SYNC_INTERVAL - 1
    gfx = None

    def should_refresh_time(self):
        time_diff = time.monotonic() - self.localtime_refresh_ts
        return time_diff > TIME_SYNC_INTERVAL

    def time_refreshed(self):
        self.localtime_refresh_ts = time.monotonic()

    def should_refresh_weather(self):
        time_diff = time.monotonic() - self.weather_refresh_ts
        return time_diff > WEATHER_SYNC_INTERVAL

    def weather_refreshed(self):
        self.weather_refresh_ts = time.monotonic()

context = Context()
context.gfx = display_graphics.Display_Graphics(
    matrix.display, logger,
    am_pm=False, units=UNITS
)
logger.debug('== Context loaded')

def update_time():
    try:
        network.get_local_time()
    except BaseException as e:
        logger.warning(f'!! Failed to update time: {traceback.format_exception(type(e), e, e.__traceback__)}')
        pass

    time_struct = time.localtime()
    # RTC.datetime = time_struct
    return time_struct

def maybe_render(context):
    # only query the online time once per hour (and on first run)
    if context.should_refresh_time():
        time_struct = update_time()
        logger.debug(f'== GET/time @ {time_struct}')
        context.time_refreshed()

    # only query the weather every 10 minutes (and on first run)
    if context.should_refresh_weather():
        logger.debug(f'== GET/weather REQ: {DATA_SOURCE}')
        value = network.fetch_data(DATA_SOURCE)
        gfx.display_weather(value)

        context.weather_refreshed()
        logger.debug(f'== GET/weather @ {time.localtime()}')

    is_new_state = gfx.display_clock(time_tuple=time.localtime())
    if is_new_state:
        gfx.render()

context = Context()
while True:
    try:
        maybe_render(context)
    except BaseException as e: # catchall
        logger.error(f'!! Render failure: {traceback.format_exception(type(e), e, e.__traceback__)}')
        time.sleep(30)  # Sleep for a bit in case it's intermittent

    # Pause between labels
    time.sleep(SCROLL_HOLD_TIME)
