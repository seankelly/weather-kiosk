let temps;

function parse_forecast(json) {
    parse_gridpoints_forecast(json);
    parse_forecast_table(json.table);
}

function parse_gridpoints_forecast(json) {
    // "now" is the next hour so is close to the current temperature.
    table = json.table;
    now = table[0];

    // "current_period" is the current day/night period. It will cover the
    // entire time the sun is up or down respectively. The associated
    // temperature is the predicted high or low.
    forecast = json.forecast;
    periods = forecast.periods;
    current_period = periods[0];

    temperature = current_period.temperature;
    temperature_unit = current_period.temperatureUnit;
    temperature_id = document.getElementById('temperature');
    temperature_id.innerHTML = `<h1>Now: ${now.temperature}  °${temperature_unit}</h1><h1>Predicted: ${temperature} °${temperature_unit}</h1>`;

    desc = current_period.detailedForecast;
    weather_info_id = document.getElementById('weather-info');
    weather_info_id.innerHTML = `<h2>${desc}</h2>`;
}

function parse_forecast_table(json) {
    // Convert object of arrays to array of objects. The "times" object is
    // known to exist and is the x axis so use that as the starting point.
    let time_parse = d3.timeParse('%Y-%m-%dT%H:%M:%S%Z');

    // Each group must look like:
    // {
    //   map name => [
    //      {
    //          point1: value1
    //          point2: value2,
    //          ...
    //          x: x,
    //      },
    //      additional points...
    //   ],
    //   additional maps...
    //  }

    let measurements = new Map();
    for (let index in json) {
        const entry = json[index];
        const time = time_parse(entry.time);

        for (measure in entry) {
            if (measure === 'time') {
                continue;
            }
            let m = [];
            if (measurements.has(measure)) {
                m = measurements.get(measure);
            }
            field = {
                time: time,
                value: entry[measure],
            };
            m.push(field);
            measurements.set(measure, m);
        }
    }

    let temperature_points = new Map();
    temperature_points.set('temperature', measurements.get('temperature'));
    temperature_points.set('dew_point', measurements.get('dew_point'));
    let sky_cover = new Map();
    sky_cover.set('cloud_amount', measurements.get('cloud_amount'));
    sky_cover.set('precipitation_probability', measurements.get('precipitation_probability'));
    let precipitation_amount = new Map();
    precipitation_amount.set('precipitation_amount', measurements.get('qpf'));

    const temperature_colors = d3.scaleOrdinal()
        .range(['#ff0000', '#009900']);

    const sky_cover_colors = d3.scaleOrdinal()
        .range(['#0000cc', '#996633']);

    const precipitation_amount_colors = d3.scaleOrdinal()
        .range(['#996633', 'black']);

    temps = temperature_points;
    graph_forecast_table(temperature_points, 'temperature-graph', temperature_colors);
    graph_forecast_table(sky_cover, 'precipitation-potential', sky_cover_colors);
    graph_forecast_table(precipitation_amount, 'precipitation-amount',
        precipitation_amount_colors, '.2f');
}

function graph_forecast_table(points, element_id, colors, y_axis_format) {
    if (y_axis_format === undefined) {
        y_axis_format = '.0f';
    }

    let temp_graph = document.getElementById(element_id);

    let graph_dimensions = {
        height: 300,
        width: 300,
        top: 10,
        right: 20,
        bottom: 40,
        left: 30,
    };
    graph_dimensions.width = temp_graph.clientWidth - graph_dimensions.left - graph_dimensions.right;

    let svg = d3.select(`#${element_id}`)
        .append('svg')
        .attr('height', graph_dimensions.height + graph_dimensions.top + graph_dimensions.bottom)
        .attr('width', graph_dimensions.width + graph_dimensions.left + graph_dimensions.right)
        .append('g')
        .attr('transform', `translate(${graph_dimensions.left}, ${graph_dimensions.top})`)
    ;

    // Flatten a Map of Array of Objects to the minimum and maximum of the
    // given property of all those Objects.
    function domain_extent(map, property) {
        let extents = []
        for (let v of map.values()) {
            extents.push(d3.extent(v, (d) => d[property]));
        }
        extent = d3.extent(extents.flat());
        // Increase minimum and maximum by one to ensure the line(s) won't
        // obscure the axis.
        /*
        if (typeof extent[0] === 'number') {
            extent[0] -= 1;
            extent[1] += 1;
        }
        */
        return extent;
    }

    const x = d3.scaleTime()
        .domain(domain_extent(points, 'time'))
        .range([0, graph_dimensions.width]);
    svg.append('g')
        .attr('transform', `translate(0, ${graph_dimensions.height})`)
        .call(d3.axisBottom(x)
            .tickSize(-graph_dimensions.height));

    const y = d3.scaleLinear()
        .domain(domain_extent(points, 'value'))
        .range([graph_dimensions.height, 0])
        .nice();
    svg.append('g')
        .attr('class', 'grid')
        .call(d3.axisLeft(y)
            .tickSize(-graph_dimensions.width)
            .tickFormat(d3.format(y_axis_format)));

    svg.selectAll('.line')
        .data(points)
        .join('path')
            .attr('stroke', (d) => colors(d[0]))
            .attr('stroke-width', 2.5)
            .attr('fill', 'none')
            .attr('d', function(d) {
                return d3.line()
                    .x((d) => x(d.time))
                    .y((d) => y(d.value))
                    (d[1]);
            });
}

function refresh() {
    let resp = fetch("./forecast.json")
        .then((response) => response.json())
        .then(parse_forecast);
}

refresh();
