#!/usr/bin/env python3

import pika
import json

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost')
)

channel = connection.channel()

channel.exchange_declare(
    exchange = 'boundingboxes',
    exchange_type = 'topic'
)

# Let the server choose a random queue name for us
# 'exclusive' means to delete the queue once the consumer connection is closed
# https://www.rabbitmq.com/tutorials/tutorial-three-python.html
result = channel.queue_declare('', exclusive=True)
queue_name = result.method.queue

binding_keys = ["#"]

for binding_key in binding_keys:
    channel.queue_bind(
        exchange='boundingboxes',
        queue = queue_name,
        routing_key=binding_key
    )

print(' [x] waiting for logs. To exit press CTRL + C')

def callback(ch, method, properties, body):
    # print(f" [x] {method.routing_key}:{body}")
    print(f" [x] Message received from {method.routing_key}")
    payload = json.loads(body)
    print(payload)

channel.basic_consume(
    queue = queue_name,
    on_message_callback=callback,
    auto_ack = True
)

channel.start_consuming()
