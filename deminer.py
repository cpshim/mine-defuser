import hashlib
import pika


def decrypt_mine(num):
    print(f"Deminer #{num}")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='demine_queue')

    def callback(ch, method, properties, body):
        x = body.decode("utf-8")
        info = x.split("%")
        print(f"Moving to location ({info[2]}, {info[3]}) to defuse mine {info[1]}")

        pin = 0
        while not hashlib.sha256(f'{pin}{info[0]}'.encode()).hexdigest().startswith("000000"):
            pin += 1
        print(hashlib.sha256(f'{pin}{info[0]}'.encode()).hexdigest())

        publish_pin(pin)

    channel.basic_consume(queue='demine_queue', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()


def publish_pin(pin):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    rabbit_channel = connection.channel()

    rabbit_channel.queue_declare(queue='defused_mines')

    rabbit_channel.basic_publish(exchange='',
                                 routing_key='defused_mines',
                                 body=f'{pin}')
    connection.close()


if __name__ == '__main__':
    decrypt_mine(input("Enter deminer number: "))
