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
from digitalio import DigitalInOut, Direction, Pull
from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix
import display_graphics

TIME_SYNC_INTERVAL = 60 * 60 * 6  # 6 hours
WEATHER_SYNC_INTERVAL = 60 * 10  # 10 mins

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("== WiFi secrets are kept in secrets.py, please add them there!")
    raise

if hasattr(board, "D12"):
    jumper = DigitalInOut(board.D12)
    jumper.direction = Direction.INPUT
    jumper.pull = Pull.UP
    is_metric = jumper.value
elif hasattr(board, "BUTTON_DOWN") and hasattr(board, "BUTTON_UP"):
    button_down = DigitalInOut(board.BUTTON_DOWN)
    button_down.switch_to_input(pull=Pull.UP)

    button_up = DigitalInOut(board.BUTTON_UP)
    button_up.switch_to_input(pull=Pull.UP)
    if not button_down.value:
        print("== Down Button Pressed")
        microcontroller.nvm[0] = 1
    elif not button_up.value:
        print("== Up Button Pressed")
        microcontroller.nvm[0] = 0
    print(microcontroller.nvm[0])
    is_metric = microcontroller.nvm[0]
else:
    is_metric = True

if is_metric:
    UNITS = "metric"  # can pick 'imperial' or 'metric' as part of URL query
else:
    UNITS = "imperial"
print('== Jumper set to {UNITS}')

# # Use cityname, country code where countrycode is ISO3166 format.
# # E.g. "New York, US" or "London, GB"
# LOCATION = "Oakland, CA, US"
# print("== Getting weather for {}".format(LOCATION))
# Set up from where we'll be fetching data
# DATA_SOURCE = (
#     f'http://api.openweathermap.org/data/2.5/weather?q='
#     f'{LOCATION}'
#     f'&units={UNITS}'
#     f'&appid={secrets["openweather_token"]}'
# )
DATA_SOURCE = (
    f'http://api.openweathermap.org/data/2.5/weather'
    f'?lat={secrets["latitude"]}'
    f'&lon={secrets["longitude"]}'
    f'&units={UNITS}'
    f'&appid={secrets["openweather_token"]}'
)
# You'll need to get a token from openweather.org, looks like 'b6907d289e10d714a6e88b30761fae22'
# it goes in your secrets.py file on a line such as:
# 'openweather_token' : 'your_big_humongous_gigantor_token',
DATA_LOCATION = []
SCROLL_HOLD_TIME = 0  # set this to hold each line before finishing scroll

# --- Display setup ---
matrix = Matrix()
network = Network(status_neopixel=board.NEOPIXEL, debug=True)
if UNITS in ("imperial", "metric"):
    # gfx = openweather_graphics.OpenWeather_Graphics(
    gfx = display_graphics.Display_Graphics(
        matrix.display, am_pm=False, units=UNITS
    )

print("== gfx loaded")

def update_time():
    network.get_local_time()

    time_struct = time.localtime()
    # RTC.datetime = time_struct
    return time_struct

localtime_refresh_ts = -TIME_SYNC_INTERVAL - 1
weather_refresh_ts = -WEATHER_SYNC_INTERVAL - 1
prev_time = (0,0)
while True:
    # only query the online time once per hour (and on first run)
    if (time.monotonic() - localtime_refresh_ts) > TIME_SYNC_INTERVAL:
        try:
            time_struct = update_time()
            print(f'== GET/time @ {time_struct}')
            localtime_refresh_ts = time.monotonic()
        except RuntimeError as e:
            print('!! Some error occured. Retrying', e)
            continue

    # only query the weather every 10 minutes (and on first run)
    if (time.monotonic() - weather_refresh_ts) > WEATHER_SYNC_INTERVAL:
        try:
            print(f'== GET/weather REQ: {DATA_SOURCE} {DATA_LOCATION}')
            value = network.fetch_data(DATA_SOURCE, json_path=(DATA_LOCATION,))
            gfx.display_weather(value)
            weather_refresh_ts = time.monotonic()
            print(f'== GET/weather @ {time.localtime()}')
        except RuntimeError as e:
            print('!! Some error occured. Retrying', e)
            continue
        
    gfx.display_clock(time_tuple=time.localtime())
    # gfx.scroll_next_label()
    # Pause between labels
    time.sleep(SCROLL_HOLD_TIME)
