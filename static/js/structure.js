$(document).ready(function() {
  var namespace = '/';
  var session = ''

  var socket = io(namespace, {'path': '/voicebot_demo_subred/socket.io'});
  socket.on('connect', function() {
      socket.emit('my_event', {data: 'I\'m connected!'});
  });

  function resetObjects() {
    $('#objects').html('<tr class="eventhover"><td style="width: 25%;">&nbsp</td><td style="width: 25%;">&nbsp</td><td style="width: 25%;">&nbsp</td><td style="width: 25%;">&nbsp</td></tr><tr class="eventhover"><td style="width: 25%;">&nbsp</td><td style="width: 25%;">&nbsp</td><td style="width: 25%;">&nbsp</td><td style="width: 25%;">&nbsp</td></tr><tr class="eventhover"><td style="width: 25%;">&nbsp</td><td style="width: 25%;">&nbsp</td><td style="width: 25%;">&nbsp</td><td style="width: 25%;">&nbsp</td></tr>');
  }

  function resetEntities() {
    $('#entities').html('<tr class="eventhover"><td style="width: 50%;">&nbsp</td><td style="width: 50%;">&nbsp</td></tr><tr class="eventhover"><td style="width: 50%;">&nbsp</td><td style="width: 50%;">&nbsp</td></tr><tr class="eventhover"><td style="width: 50%;">&nbsp</td><td style="width: 50%;">&nbsp</td></tr>');
  }

  socket.on('user_interaction', function(msg) {
    // Message   

    if (msg.session != session){
      session = msg.session;
      $('#chat').empty();
      $("#graph").empty();
      $('#predictions').empty();
      resetObjects();
      resetEntities();
    }
    $('#chat').append("<div class=\"col-xs-11 corners text-center user-interaction\"><div class=\"blocktittle-interaction green-border\">Usuario</div><div id=\"entry\" class=\"text\">" + msg.message + "</div></div>")
      .promise().then(function(){
        $("#chat-scrollable").queue(function(){
            $(this).animate({ scrollTop: $('#chat').height() }, 1000).dequeue();
        });
      });    
  });

  socket.on('answer_interaction', function(msg) {
    // Answer
    $('#chat').append("<div class=\"col-xs-12\"><div class=\"col-xs-1\"></div><div class=\"col-xs-11 agent-interaction corners text-center float-right\"><div class=\"blocktittle-interaction green-border\">Agente</div><div id=\"out\" class=\"text\">" + msg.answer + "</div></div></div> ")
      .promise().then(function(){
        $("#chat-scrollable").queue(function(){
            $(this).animate({ scrollTop: $('#chat').height() }, 1000).dequeue();
        });
      });    
  });

  socket.on('update_entities', function(msg) { 
    // Entities
    jQuery.each(msg.entities, function() {      
      $( "#" + String(this['label']) ).remove();
      $('#entities').prepend('<tr id="' + this['label'] + '" class="eventhover"><td style="width: 50%;">' + this['label'] + '</td><td style="width: 50%;">' + this['text'] + '</td></tr>').html();
    });
  });

  socket.on('model_interaction', function(msg) {    
      // Graph
      $("#graph").empty()
      d = new Date();
      var viewer = OpenSeadragon({
        id: "graph",
        prefixUrl: "/voicebot_demo_subred/static/images/openseadragon/",
        tileSources: {
          type: 'image',
          url:  '/voicebot_demo_subred/static/images/graph_complete.png?' + d.getTime()
        },
        defaultZoomLevel: 0.5,
        minZoomLevel: 	  0.1,
        maxZoomLevel: 	  100,
        visibilityRatio: 	  1,
      });


      // Objects
      $('#objects').empty()
      jQuery.each(msg.objects, function() {
        $('#objects').append('<tr class="eventhover"><td style="width: 25%;">' + this[0] + '</td><td style="width: 25%;">' + this[1] + '</td><td style="width: 25%;">' + this[2] + '</td><td style="width: 25%;">' + this[3] + '</td></tr>').html();
      });

      // Entities      
      $('#entities').empty()
      jQuery.each(msg.needed_entites, function() {
        $('#entities').append('<tr id=' + this + ' class="redrow eventhover"><td style="width: 50%;">' + this + '</td><td style="width: 50%;"> ? </td></tr>')
      });
      jQuery.each(msg.entities, function() {
        $( "#" + String(this['label']) ).remove();

        $('#entities').prepend('<tr id="' + this['label'] + '" class="eventhover"><td style="width: 50%;">' + this['label'] + '</td><td style="width: 50%;">' + this['text'] + '</td></tr>').html();
      });

      // Intention graph
      data = msg.prediction;

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
        },
        autosize: true
      };

      elementDOM = document.getElementById('predictions');      
      Plotly.newPlot(elementDOM, data, layout, {displayModeBar: false});
  });
});
