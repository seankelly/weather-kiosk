#!/usr/bin/env python3

import argparse
import json
import random
import time
from datetime import datetime
from xml.etree import ElementTree

import requests
import yaml


# Wait up to five minutes when running with --cron option.
CONFIG_CRON_WAIT = 5 * 60.0
CONFIG_DEFAULT_PATH = './weather_config.yaml'
CONFIG_DEFAULT_OUTPUT = './forecast.json'
NWS_FORECAST_TABLE_URL = ('https://forecast.weather.gov/MapClick.php?lat={latitude}&'
                          'lon={longitude}&FcstType=digitalDWML')
NWS_API_GRIDPOINTS_URL = 'https://api.weather.gov/gridpoints/{office}/{gridx},{gridy}'
NWS_API_GRIDPOINTS_FORECAST_URL = NWS_API_GRIDPOINTS_URL + '/forecast'


class NwsGridpointsForecast:

    def __init__(self, gridpoints):
        self._json = None
        self.office = None
        self.gridx = None
        self.gridy = None
        self._config(gridpoints)

    def _config(self, gridpoints):
        self.office = gridpoints.get('office')
        self.gridx = gridpoints.get('gridX')
        self.gridy = gridpoints.get('gridY')

    def run(self):
        json = self.fetch()
        return json.get('properties')

    def fetch(self):
        if self.office is None or self.gridx is None or self.gridy is None:
            return {}
        forecast_url = NWS_API_GRIDPOINTS_FORECAST_URL.format(
            office=self.office, gridx=self.gridx, gridy=self.gridy)
        req = requests.get(forecast_url)
        req.raise_for_status()
        self._json = req.json()
        return self._json


class NwsForecastTable:

    def __init__(self, latitude, longitude):
        self._xml = None
        self._table = {}
        self.latitude = latitude
        self.longitude = longitude

    def run(self):
        xml = self.fetch()
        forecast_table = self.parse(xml)
        return forecast_table

    def run_with_input(self, xml_etree):
        self._xml = xml_etree
        forecast_table = self.parse(xml_etree)
        return forecast_table

    def fetch(self):
        forecast_url = NWS_FORECAST_TABLE_URL.format(latitude=self.latitude,
                                                     longitude=self.longitude)
        req = requests.get(forecast_url)
        req.raise_for_status()
        self._xml = ElementTree.fromstring(req.text)
        return self._xml

    def parse(self, forecast):
        def get_values(forecast, xpath, type=int):
            values = []
            for node in forecast.findall(xpath):
                if node.text:
                    values.append(type(node.text))
                else:
                    values.append(None)
            return values

        valid_times = []
        for node in forecast.findall('.//start-valid-time'):
            valid_times.append(node.text)
        temperatures = get_values(forecast, './/temperature[@type="hourly"]/value')
        dew_points = get_values(forecast, './/temperature[@type="dew point"]/value')
        cloud_amount = get_values(forecast, './/cloud-amount/value')
        precipitation_probability = get_values(forecast, './/probability-of-precipitation/value')
        qpf = get_values(forecast, './/hourly-qpf/value', type=float)

        forecast_output = []
        for item in zip(valid_times, temperatures, dew_points, cloud_amount,
                        precipitation_probability, qpf):
            entry = {
                'time': item[0],
                'temperature': item[1],
                'dew_point': item[2],
                'cloud_amount': item[3],
                'precipitation_probability': item[4],
                'qpf': item[5],
            }
            forecast_output.append(entry)
        self._table = forecast_output
        return forecast_output


def options():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cron', action='store_true', default=False)
    parser.add_argument('--config', default=CONFIG_DEFAULT_PATH)
    parser.add_argument('--input', metavar="FORECAST_XML")
    parser.add_argument('--output', metavar="OUTPUT_JSON", default=CONFIG_DEFAULT_OUTPUT)
    args = parser.parse_args()
    return args


def main():
    args = options()
    forecast_output = {}

    # Allow pausing a random amount of time to prevent running _exactly_ at the
    # cron second. This can avoid thundering herd issues.
    if args.cron:
        cron_wait = random.uniform(0.0, CONFIG_CRON_WAIT)
        print(f"Sleeping {cron_wait:0.2f} seconds because running in cron...")
        time.sleep(cron_wait)

    with open(args.config) as config_file:
        config = yaml.safe_load(config_file)

    if not args.input:
        with open(args.config) as config_file:
            config = yaml.safe_load(config_file)
        location = config.get('location')
        if not location:
            print("Missing location key.")
            return
        latitude = location.get('latitude')
        longitude = location.get('longitude')
        if not latitude or not longitude:
            print("Missing latitude or longitude key in location.")
            return
        forecast_table = NwsForecastTable(latitude, longitude)
        forecast_output['table'] = forecast_table.run()
    else:
        with open(args.input) as forecast_input:
            forecast = ElementTree.fromstring(forecast_input)
        forecast_table = NwsForecastTable(None, None)
        forecast_output['table'] = forecast_table.run_with_input(forecast)

    if 'gridpoints' in config:
        gridpoints_forecast = NwsGridpointsForecast(config['gridpoints'])
        forecast_output['forecast'] = gridpoints_forecast.run()

    with open(args.output, 'w') as output:
        json.dump(forecast_output, output)


if __name__ == '__main__':
    main()
