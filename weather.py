#    Friendly Telegram (telegram userbot)
#    Copyright (C) 2018-2019 The Authors

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.

#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

# requires: pyowm

import logging
import pyowm
import math

from .. import loader, utils

from ..utils import escape_html as eh

logger = logging.getLogger(__name__)


def register(cb):
    cb(WeatherMod())


def deg_to_text(deg):
    if deg is None:
        return _("unknown")
    return ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW",
            "SW", "WSW", "W", "WNW", "NW", "NNW"][round(deg / 22.5) % 16]


def round_to_sf(n, digits):
    return round(n, digits - 1 - int(math.floor(math.log10(abs(n)))))


@loader.tds
class WeatherMod(loader.Module):
    """Checks the weather
       Get an API key at https://openweathermap.org/appid"""
    strings = {"name": "Weather",
               "provide_api": "<b>Please provide an API key via the configuration mode.</b>",
               "invalid_temp_units": "<b>Invalid temperature units provided. Please reconfigure the module.</b>",
               "doc_default_loc": "OpenWeatherMap City ID",
               "doc_api_key": "API Key from https://openweathermap.org/appid",
               "doc_temp_units": "Temperature unit as English",
               "result": "<b>Weather in {loc} is {w} with a high of {high} and a low"
                         " of {low}, averaging at {avg} with {humid}% humidity and a {ws}mph {wd} wind.</b>"}

    def __init__(self):
        self.config = loader.ModuleConfig("DEFAULT_LOCATION", None, lambda: self.strings["doc_default_loc"],
                                          "API_KEY", None, lambda: self.strings["doc_api_key"],
                                          "TEMP_UNITS", "celsius", lambda: self.strings["doc_temp_units"])
        self._owm = None

    def config_complete(self):
        self._owm = pyowm.OWM(self.config["API_KEY"])
        self.name = self.strings["name"]

    async def weathercmd(self, message):
        """.weather [location]"""
        if self.config["API_KEY"] is None:
            await utils.answer(message, self.strings["provide_api"])
            return
        args = utils.get_args_raw(message)
        func = None
        if not args:
            func = self._owm.weather_at_id
            args = [self.config["DEFAULT_LOCATION"]]
        else:
            try:
                args = [int(args)]
                func = self._owm.weather_at_id
            except ValueError:
                coords = utils.get_args_split_by(message, ",")
                if len(coords) == 2:
                    try:
                        args = [int(coord.strip()) for coord in coords]
                        func = self._owm.weather_at_coords
                    except ValueError:
                        pass
        if func is None:
            func = self._owm.weather_at_place
            args = [args]
        logger.debug(func)
        logger.debug(args)
        w = await utils.run_sync(func, *args)
        logger.debug(_("Weather at {args} is {w}").format(args=args, w=w))
        try:
            weather = w.get_weather()
            temp = weather.get_temperature(self.config["TEMP_UNITS"])
        except ValueError:
            await utils.answer(message, self.strings["invalid_temp_units"])
            return
        ret = self.strings["result"].format(loc=eh(w.get_location().get_name()),
                                            w=eh(w.get_weather().get_detailed_status().lower()),
                                            high=eh(temp["temp_max"]), low=eh(temp["temp_min"]), avg=eh(temp["temp"]),
                                            humid=eh(weather.get_humidity()),
                                            ws=eh(round_to_sf(weather.get_wind("miles_hour")["speed"], 3)),
                                            wd=eh(deg_to_text(weather.get_wind().get("deg", None))))
        await utils.answer(message, ret)
