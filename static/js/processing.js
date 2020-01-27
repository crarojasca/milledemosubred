$(document).ready(function() {
    namespace = '/socketflow';

    var socket = io(namespace);

    // var socket = io.connect('192.168.222.67:8003', {
    //   'path': '/partofspeech/socket.io';
    // });

    socket.on('connect', function() {
        socket.emit('my_event', {data: 'I\'m connected!'});
    });

    socket.on('text_graph', function(msg) {
        $('#entry').text(msg.message).html();
        d = new Date();
        $("#graph").attr("src", "/partofspeech/static/graph.png?"+d.getTime());
    });

    socket.on('prediction', function(msg) {
        data = JSON.parse((msg));

        var trace1 = {
          x: data['classes'],
          y: data['prediction'],
          name: 'Predictions',
          type: 'bar',
          marker: {
            opacity: 0.7,
          }
        };

        var trace2 = {
          x: data['classes'],
          y: data['threshold'],
          name: 'Thresholds',
          yaxis: 'y2',
          type: 'bar',
          marker: {
            opacity: 0.5
          }
        };

        var data = [trace1, trace2];

        var layout = {
          barmode: 'stack',
          yaxis: {range: [0, 1]},
          yaxis2: {
            range: [0, 1],
            overlaying: 'y'
          }
        };

        PREDICTS = document.getElementById('predictions');
        Plotly.newPlot(PREDICTS, data, layout, {displayModeBar: false});
    });


});
