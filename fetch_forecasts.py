#!/usr/bin/env python3

import argparse
import json
from datetime import datetime
from xml.etree import ElementTree

import requests
import yaml


CONFIG_DEFAULT_PATH = './weather_config.yaml'
CONFIG_DEFAULT_OUTPUT = './forecast.json'
NWS_FORECAST_TABLE_URL = ('https://forecast.weather.gov/MapClick.php?lat={latitude}&'
                          'lon={longitude}&FcstType=digitalDWML')


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
                try:
                    values.append(type(node.text))
                except ValueError:
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
    parser.add_argument('--config', default=CONFIG_DEFAULT_PATH)
    parser.add_argument('--input', metavar="FORECAST_XML")
    parser.add_argument('--output', metavar="OUTPUT_JSON", default=CONFIG_DEFAULT_OUTPUT)
    args = parser.parse_args()
    return args


def main():
    args = options()
    forecast_output = {}

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

    with open(args.output, 'w') as output:
        json.dump(forecast_output, output)


if __name__ == '__main__':
    main()
