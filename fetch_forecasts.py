#!/usr/bin/env python3

import argparse
import json
from datetime import datetime
from xml.etree import ElementTree

import requests
import yaml


def parse_forecast(forecast):
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

    print(forecast_output)
    return forecast_output


def options():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    parser.add_argument('--input', metavar="FORECAST_XML")
    args = parser.parse_args()
    return args


def main():
    args = options()
    if args.input:
        with open(args.input) as forecast_input:
            forecast = ElementTree.parse(forecast_input)
            forecast_output = parse_forecast(forecast)
        with open('forecast-table.json', 'w') as output:
            json.dump(forecast_output, output)


if __name__ == '__main__':
    main()
