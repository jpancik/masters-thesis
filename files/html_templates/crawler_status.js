// Source: https://bl.ocks.org/laxmikanta415/dc33fe11344bf5568918ba690743e06f
/*
Copyright 2018 Laxmikanta Nayak

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of
the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

createChart = function(data) {
    var width = document.getElementById('pie-chart').clientWidth;
    var height = width / 2;
    var margin = 10;

    var totalCount = 0;
    for (var websiteDomain in data) {
        totalCount += data[websiteDomain];
    }
    var minCount = totalCount/50;

    var radius = height / 2 - margin;

    var svg = d3.select("#pie-chart")
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

    var keys = [];
    for (var websiteDomain in data) {
        keys.push(websiteDomain);
    }

    var color = d3.scaleOrdinal()
        .domain(keys)
        .range(d3.schemeDark2);

    var pie = d3.pie()
        .sort(null)
        .value(function (d) {
            return d.value;
        });
    var data_ready = pie(d3.entries(data));

    var arc = d3.arc().innerRadius(radius * 0.5).outerRadius(radius * 0.8);
    var outerArc = d3.arc().innerRadius(radius * 0.9).outerRadius(radius * 0.9);

    svg
        .selectAll('allSlices')
        .data(data_ready)
        .enter()
        .append('path')
        .attr('d', arc)
        .attr('fill', function (d) {
            return (color(d.data.key))
        })
        .attr("stroke", "white")
        .style("stroke-width", "1px")
        .style("opacity", 0.7)
        .on("mouseover", function (d, i) {
            svg.append("text")
                .attr("dy", "-0.5em")
                .style("text-anchor", "middle")
                .style("font-size", 20)
                .attr("class", "label1")
                .style("fill", function (d, i) {
                    return "black";
                })
                .text(d.data.key);
            svg.append("text")
                .attr("dy", "1.0em")
                .style("text-anchor", "middle")
                .style("font-size", 20)
                .attr("class", "label2")
                .style("fill", function (d, i) {
                    return "black";
                })
                .text(d.data.value + ' articles');
        })
        .on("mouseout", function (d) {
            svg.select(".label1").remove();
            svg.select(".label2").remove();
        });

    svg
        .selectAll('allPolylines')
        .data(data_ready)
        .enter()
        .filter(function(d) {
            return d.data.value > minCount;
        })
        .append('polyline')
        .attr("stroke", "black")
        .style("fill", "none")
        .attr("stroke-width", 1)
        .attr('points', function (d) {
            var posA = arc.centroid(d);
            var posB = outerArc.centroid(d);
            var posC = outerArc.centroid(d);
            var midangle = d.startAngle + (d.endAngle - d.startAngle) / 2;
            posC[0] = radius * 0.95 * (midangle < Math.PI ? 1 : -1);
            return [posA, posB, posC]
        });

    svg
        .selectAll('allLabels')
        .data(data_ready)
        .enter()
        .filter(function(d) {
            return d.data.value > minCount;
        })
        .append('text')
        .text(function (d) {
            return d.data.key
        })
        .attr('transform', function (d) {
            var pos = outerArc.centroid(d);
            var midangle = d.startAngle + (d.endAngle - d.startAngle) / 2;
            pos[0] = radius * 0.99 * (midangle < Math.PI ? 1 : -1);
            return 'translate(' + pos + ')';
        })
        .style('text-anchor', function (d) {
            var midangle = d.startAngle + (d.endAngle - d.startAngle) / 2;
            return (midangle < Math.PI ? 'start' : 'end')
        });
};