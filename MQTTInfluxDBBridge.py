import re
from typing import NamedTuple

import paho.mqtt.client as mqtt
from influxdb import InfluxDBClient

INFLUXDB_ADDRESS = 'localhost'
INFLUXDB_USER = 'mqtt'
INFLUXDB_PASSWORD = 'mqtt'
INFLUXDB_DATABASE = 'smartmeter'

MQTT_ADDRESS = '172.28.255.239'
MQTT_USER = 'pi'
MQTT_PASSWORD = 'raspberry'
MQTT_TOPIC = 'smart_meter_events/raw'
MQTT_CLIENT_ID = 'MQTTInfluxDBBridge'

influxdb_client = InfluxDBClient(INFLUXDB_ADDRESS, 8086, INFLUXDB_USER, INFLUXDB_PASSWORD, None)

class SensorData(NamedTuple):
    timestamp: str
    voltage: float
    pf: float
    power: float

def on_connect(client, userdata, flags, rc):
    """ The callback for when the client receives a CONNACK response from the server."""
    print('Connected with result code ' + str(rc))
    client.subscribe(MQTT_TOPIC)

def _parse_mqtt_message(topic, payload):
    vector = payload.split(';')
    return SensorData(vector[0], float(vector[2]), float(vector[3]), float(vector[4]))

def _send_sensor_data_to_influxdb(sensor_data):
    json_body = [
        {
            'measurement': 'voltage',
            'tags': { 'timestamp': sensor_data.timestamp },
            'fields': {
                'value': sensor_data.voltage
            }
        },
        {
            'measurement': 'pf',
            'tags': { 'timestamp': sensor_data.timestamp },
            'fields': {
                'pf': sensor_data.pf / 1000.0
            }
        },
        {
            'measurement': 'power',
            'tags': { 'timestamp': sensor_data.timestamp },
            'fields': {
                'power': sensor_data.power
            }
        }
    ]
    influxdb_client.write_points(json_body)

def on_message(client, userdata, msg):
    """The callback for when a PUBLISH message is received from the server."""
    print(msg.topic + ' ' + str(msg.payload))
    sensor_data = _parse_mqtt_message(msg.topic, msg.payload.decode('utf-8'))
    if sensor_data is not None:
        _send_sensor_data_to_influxdb(sensor_data)

def _init_influxdb_database():
    databases = influxdb_client.get_list_database()
    if len(list(filter(lambda x: x['name'] == INFLUXDB_DATABASE, databases))) == 0:
        influxdb_client.create_database(INFLUXDB_DATABASE)
    influxdb_client.switch_database(INFLUXDB_DATABASE)

def main():
    _init_influxdb_database()

    mqtt_client = mqtt.Client(MQTT_CLIENT_ID)
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    mqtt_client.connect(MQTT_ADDRESS, 1883)
    mqtt_client.loop_forever()


if __name__ == '__main__':
    print('MQTT to InfluxDB bridge')
    main()


