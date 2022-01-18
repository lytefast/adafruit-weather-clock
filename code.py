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
import gc
import board
import time
import adafruit_logging as logging
import microcontroller
import display_graphics
import traceback

from digitalio import DigitalInOut, Direction, Pull
from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrixportal import MatrixPortal
from aio_handler import AIOHandler


ONE_MIN = 60
ONE_HOUR = 60 * ONE_MIN

TIME_SYNC_INTERVAL = ONE_HOUR
WEATHER_SYNC_INTERVAL = 20 * ONE_MIN

SCROLL_HOLD_TIME = 0.2  # set this to hold each line before finishing scroll

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print('== WiFi secrets are kept in secrets.py, please add them there!')
    raise

# --- Display setup ---
matrixportal = MatrixPortal(
    default_bg='./loading.bmp',
    status_neopixel=board.NEOPIXEL, debug=True)

logger = logging.getLogger('aio')
logger.addHandler(AIOHandler('adafruit-weather-clock', matrixportal.network, logging.INFO))
logger.setLevel(logging.INFO)

gc.collect()

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
logger.debug(f'== Jumper set to {UNITS}')

# Use cityname, country code where countrycode is ISO3166 format.
# E.g. "New York, US" or "London, GB"
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

class Context:
    localtime_refresh_ts = -TIME_SYNC_INTERVAL - 1
    weather_refresh_ts = -WEATHER_SYNC_INTERVAL - 1
    gfx = None

context = Context()
context.gfx = display_graphics.DisplayGraphics(
    matrixportal, logger,
    am_pm=False, celsius=is_metric, meters_speed=is_metric,
)
gc.collect()
logger.debug('== Context loaded')

def update_time(context):
    try:
        matrixportal.network.get_local_time()
    except BaseException as e:
        logger.warning(f'!! Failed to update time: {traceback.format_exception(type(e), e, e.__traceback__)}')
        pass
    gc.collect()

    time_struct = time.localtime()
    # RTC.datetime = time_struct
    return time_struct


logger.info('!! Starting main loop !!')
matrixportal.set_background(0)
while True:
    try:
        is_render = False
        # only query the online time once per hour (and on first run)
        if (time.monotonic() - context.localtime_refresh_ts) > TIME_SYNC_INTERVAL:
            gc.collect()
            logger.info(f'FETCH time')
            time_struct = update_time(context)
            context.localtime_refresh_ts = time.monotonic()

        # only query the weather every 10 minutes (and on first run)
        if (time.monotonic() - context.weather_refresh_ts) > WEATHER_SYNC_INTERVAL:
            gc.collect()
            logger.info(f'FETCH weather')
            value = matrixportal.network.fetch_data(DATA_SOURCE, json_path=([],))
            context.gfx.update_weather(value[0])
            context.weather_refresh_ts = time.monotonic()
            is_render = True

        is_render |= bool(context.gfx.update_clock(time_tuple=time.localtime()))
    except BaseException as e: # catchall
        gc.collect()
        print('FAIL Render')
        logger.error(f'FAIL Render: {traceback.format_exception(type(e), e, e.__traceback__)}')
        gc.collect()
        time.sleep(10)  # Sleep for a bit in case it's intermittent

    # Pause between labels
    context.gfx.matrixportal.scroll()
    time.sleep(SCROLL_HOLD_TIME)
