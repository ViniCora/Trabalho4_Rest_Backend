import pika


class RabbitMQHelper:
    def __init__(self, exchange=None, exchange_type='direct'):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.exchange = exchange
        self.exchange_type = exchange_type

        if self.exchange:
            self.declare_exchange(self.exchange, self.exchange_type)

    def declare_queue(self, queue, exclusive=True, durable=True):
        return self.channel.queue_declare(queue=queue, durable=durable, exclusive=exclusive)

    def declare_exchange(self, exchange=None, exchange_type='direct'):
        exch = exchange or self.exchange
        ex_type = exchange_type or self.exchange_type
        if exch is None:
            raise ValueError("Nenhum exchange informado para declarar")
        self.channel.exchange_declare(exchange=exch, exchange_type=ex_type)

    def publish(self, routing_key, body, exchange=None):
        exch = exchange or self.exchange or ''
        self.channel.basic_publish(
            exchange=exch,
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2
            )
        )

    def receive(self, queue_name, callback, auto_ack=True):
        self.channel.basic_consume(
            queue=queue_name, on_message_callback=callback, auto_ack=auto_ack)

    def bind_queue(self, exchange, queue_name, routing_key):
        self.channel.queue_bind(
            exchange=exchange, queue=queue_name, routing_key=routing_key)

    def consume(self):
        self.channel.start_consuming()

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()

    