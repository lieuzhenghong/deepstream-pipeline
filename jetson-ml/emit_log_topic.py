#!/usr/bin/env python3
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))

channel = connection.channel()

channel.exchange_declare(
    exchange = 'boundingboxes',
    exchange_type = 'topic'
)

routing_key = 'camera.boundingbox'
message = 'The bounding box should be here'

channel.basic_publish(
    exchange='boundingboxes',
    routing_key=routing_key,
    body=message
)

print(f" [x] Sent {routing_key}:{message}")
connection.close()