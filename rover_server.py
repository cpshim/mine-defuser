import json
import urllib.request
from concurrent import futures
import pika

import grpc
import rover_pb2
import rover_pb2_grpc

# connection = pika.BlockingConnection(pika.ConnectionParameters('localhost:5672'))
# channel = connection.channel()


class RoverGuideServicer(rover_pb2_grpc.RoverGuideServicer):
    def GetMap(self, request, context):
        print("Received client map request")
        print(request)

        terrain = []
        terrain_size = None
        line_num = 0
        file = open("map.txt", "r")  # first line is 2 numbers divided by a space, rows columns
        for x in file:
            if line_num == 0:
                terrain_size = x
            else:
                for y in x.strip():
                    terrain.append(y)
            line_num += 1
        file.close()
        print(terrain_size)
        print(terrain)

        for x in terrain:
            map_reply = rover_pb2.MapReply()
            map_reply.size = terrain_size
            map_reply.map = x
            yield map_reply

        return map_reply

    def GetCommands(self, request, context):
        print(f'https://coe892.reev.dev/lab1/rover/{request.commands}')
        contents = urllib.request.urlopen(f'https://coe892.reev.dev/lab1/rover/{request.commands}')
        data = json.loads(contents.read().decode('utf8'))
        print(data["data"]["moves"])
        commands = data["data"]["moves"]

        for command in commands:
            command_reply = rover_pb2.CommandsReply()
            command_reply.commands = command
            yield command_reply

    def GetMineNum(self, request, context):
        mine_map = []
        file = open("mines.txt", "r")
        for x in file:
            mine_map.append(x.strip())
        # print(mine_map)
        file.close()

        mine_reply = rover_pb2.MineNumReply()
        mine_reply.mine = mine_map[request.mine_number]
        return mine_reply

    def SharePIN(self, request, context):
        share_reply = rover_pb2.ShareReply()
        share_reply.message = f"Stored PIN {request.pin}"
        return share_reply

    def Success(self, request, context):
        success_reply = rover_pb2.SuccessReply()
        success_reply.message = f"{request.message}!"
        return success_reply


def subscribe_mine():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='defused_mines')

    def callback(ch, method, properties, body):
        x = body.decode("utf-8")
        print(f"Mine defused with pin {x}")

        file = open("mine_pins.txt", "a")
        file.write(f"{x}\n")
        file.close()

    channel.basic_consume(queue='defused_mines', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=3))
    rover_pb2_grpc.add_RoverGuideServicer_to_server(RoverGuideServicer(), server)
    server.add_insecure_port("localhost:5001")
    server.start()
    subscribe_mine()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
