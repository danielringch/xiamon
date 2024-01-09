import struct
import paho.mqtt.client as mqtt
from ssl import CERT_NONE
from functools import partial
from ...core import Plugin


class Mqttlogger(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Mqttlogger, self).__init__(config, outputs)

        ip, port = self.config.get('localhost:1883', 'host').split(':')
        ca = self.config.get(None, 'ca')
        tls_insecure = self.config.get(False, 'tls_insecure')
        user = self.config.get(None, 'user')
        password = self.config.get(None, 'password')

        self.__topics = {}

        self.__decoders = {
            'bool': '!?',
            'uint8': '!B',
            'int8': '!b',
            'uint16': '!H',
            'int16': '!h',
            'uint32': '!I',
            'int32': '!i',
            'uint64': '!Q',
            'int64': '!q',
            'float': '!f',
            'double': '!d',
            'utf8': '!utf8'
        }

        self.__mqtt = mqtt.Client()
        self.__mqtt.on_connect = self.__on_connect
        self.__mqtt.on_message = self.__on_message

        if ca:
            self.__mqtt.tls_set(ca_certs=ca, cert_reqs=CERT_NONE if tls_insecure else None)

        if user or password:
            self.__mqtt.username_pw_set(user, password)

        self.__mqtt.connect(ip, int(port), 60)
        self.__mqtt.loop_start()

        for topic, metadata in self.config.data['topics'].items():
            try:
                parsed_channel = Plugin.Channel[metadata['channel']]
            except:
                self.msg.error(f'Invalid channel for topic {topic}.')
                continue
            try:
                decoder = self.__decoders[metadata['type']]
            except:
                self.msg.error(f'Invalid type for topic {topic}.')
                continue
            self.__topics[topic] = partial(self.__process_message, parsed_channel, decoder)
            self.__mqtt.subscribe(topic, qos=1)

    def __on_connect(self, client, userdata, flags, rc):
        self.msg.debug(f'MQTT connected with code {rc}.')
         
    def __on_message(self, client, userdata, msg):
        callback = self.__topics.get(msg.topic, None)
        if callback is None:
            return
        callback(msg.topic, msg.payload)

    def __process_message(self, channel, type, topic, message):
        try:
            if message is None or len(message) == 0:
                data = ''
            else:
                if type == '!utf8':
                    data = message.decode('utf-8')
                else:
                    data = struct.unpack(type, message)[0]
            self.send(channel, f'MQTT message on {topic}: {data}')
        except Exception as e:
            self.msg.error(f'Unable to parse MQTT message on topic {topic}: {e}')

