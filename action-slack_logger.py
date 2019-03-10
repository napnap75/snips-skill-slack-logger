#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from snipsTools import SnipsConfigParser
from slacker import Slacker
import paho.mqtt.client as mqtt
import json
import sys

CONFIG_INI = "config.ini"

sites = {}

try:
    config = SnipsConfigParser.read_configuration_file(CONFIG_INI)
except :
    config = None

slack = Slacker(config.get('secret').get('slack-token'))

def on_connect(client, userdata, flags, rc):
    print('Connected')
    client.subscribe('hermes/hotword/#')
    client.subscribe('hermes/asr/textCaptured')
    client.subscribe('hermes/intent/#')
    client.subscribe('hermes/tts/say')

def on_hotword_detected(topic, json_msg):
    sites[json_msg['siteId']] = 'Hotword : "{}"'.format(json_msg['modelId'])

def on_text_captured(topic, json_msg):
    sites[json_msg['siteId']] += '\nASR : "{}"'.format(json_msg['text'])

def on_intent_message(topic, json_msg):
    sites[json_msg['siteId']] += '\nINTENT : "{}"'.format(json_msg['intent']['intentName'])
    if len(json_msg['slots']) > 0:
        for slot in json_msg['slots']:
          sites[json_msg['siteId']] += '\nSLOT : Name:"{}", Entity:"{}", Value:"{}"'.format(slot['slotName'], slot['entity'], slot['value']['value'])
    else:
        sites[json_msg['siteId']] += ' with no slots'

def on_tts_say(topic, json_msg):
    sites[json_msg['siteId']] += '\nTTS : "{}"'.format(json_msg['text'])

def on_end_session(topic, json_msg):
    slack.chat.post_message(config.get('secret').get('slack-channel'), sites[json_msg['siteId']], username=config.get('secret').get('slack-username'), icon_emoji=config.get('secret').get('slack-emoji'))

def on_message(client, userdata, msg):
    try:
        if msg.topic.startswith('hermes/hotword/') and msg.topic.endswith('/detected'):
            on_hotword_detected(msg.topic, json.loads(msg.payload.decode('utf-8')))
        elif msg.topic == 'hermes/asr/textCaptured':
            on_text_captured(msg.topic, json.loads(msg.payload.decode('utf-8')))
        elif msg.topic.startswith('hermes/intent/'):
            on_intent_message(msg.topic, json.loads(msg.payload.decode('utf-8')))
        elif msg.topic == 'hermes/tts/say':
            on_tts_say(msg.topic, json.loads(msg.payload.decode('utf-8')))
        elif msg.topic == 'hermes/hotword/toggleOn':
            on_end_session(msg.topic, json.loads(msg.payload.decode('utf-8')))
    except Exception as e:
        print('Exception while handling {} : '.format(msg.topic), sys.exc_info()[0])

def on_disconnect(client, userdata, rc):
    print('Disconnected')

local_mqtt = mqtt.Client()
local_mqtt.on_connect = on_connect
local_mqtt.on_disconnect = on_disconnect
local_mqtt.on_message = on_message
local_mqtt.connect(config.get('global').get('mqtt-host'), int(config.get('global').get('mqtt-port')))
local_mqtt.loop_forever()
