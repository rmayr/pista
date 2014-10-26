% include('tbstop.tpl', page='console', page_title='OwnTracks Console')


    <script src="js/mqttws31.js" type="text/javascript"></script>
    <script src="config.js" type="text/javascript"></script>

    <script type="text/javascript">
    var mqtt;
    var reconnectTimeout = 2000;

    function MQTTconnect() {
        mqtt = new Messaging.Client(
                        config.host,
                        config.port,
                        "web_" + parseInt(Math.random() * 100,
                        10));
        var options = {
            timeout: 3,
            useSSL: config.usetls,
            cleanSession: config.cleansession,
            onSuccess: onConnect,
            onFailure: function (message) {
                $('#status').val("Connection failed: " + message.errorMessage + "Retrying");
                setTimeout(MQTTconnect, reconnectTimeout);
            }
        };

        mqtt.onConnectionLost = onConnectionLost;
        mqtt.onMessageArrived = onMessageArrived;

        if (config.username != null) {
            options.userName = config.username;
            options.password = config.password;
        }
        console.log("Host="+ config.host + ", port=" + config.port + " TLS = " + config.usetls + " username=" + config.username + " password=" + config.password);
        mqtt.connect(options);
    }

    function onConnect() {
        $('#status').val('Connected to ' + config.host + ':' + config.port);
        // Connection succeeded; subscribe to our topic
        mqtt.subscribe(config.topic, {qos: 0});
        $('#topic').val(config.topic);
    }

    function onConnectionLost(response) {
        setTimeout(MQTTconnect, reconnectTimeout);
        $('#status').val("connection lost: " + response.errorMessage + ". Reconnecting");

    };

    function onMessageArrived(message) {

        var topic = message.destinationName;
        var payload = message.payloadString;

        $('#ws').prepend('<li>' + topic + ' = ' + payload + '</li>');
    };


    $(document).ready(function() {
        MQTTconnect();
    });

    </script>

    <h2>MQTT live</h2>
    <div>
        <div>Subscribed to <input type='text' id='topic' disabled />
        Status: <input type='text' id='status' size="80" disabled /></div>

        <ul id='ws' style="font-family: 'Courier New', Courier, monospace;"></ul>
    </div>


% include('tbsbot.tpl')
