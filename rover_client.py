import copy
import hashlib
import rover_pb2_grpc
import rover_pb2
import grpc
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
rabbit_channel = connection.channel()


def run():
    with grpc.insecure_channel('localhost:5001') as channel:
        stub = rover_pb2_grpc.RoverGuideStub(channel)

        rover_num = input("What rover number: ")

        # GetMap call
        map_request = rover_pb2.MapRequest(map="Get map")
        map_replies = stub.GetMap(map_request)
        terrain = []
        i = 0
        terrain_line = []
        for map_reply in map_replies:
            if i == int(map_reply.size.split(" ")[0]):
                terrain.append(terrain_line)
                terrain_line = []
                i = 0
            terrain_line.append(map_reply.map)
            i += 1
        terrain.append(terrain_line)
        print(terrain)

        # Moving the rover (from lab 1)
        direction = 180
        path = copy.deepcopy(terrain)
        path[0][0] = '*'
        mine_num = 0
        pins = []
        position = [0, 0]
        on_mine = False
        exploded = False
        print(position)

        # GetCommand call
        command_request = rover_pb2.CommandsRequest(commands=rover_num)
        command_replies = stub.GetCommands(command_request)
        for command_reply in command_replies:
            print(position)
            if exploded:
                break
            if terrain[position[0]][position[1]] == '1':
                on_mine = True
            if command_reply.commands == 'L' or command_reply.commands == 'R':
                direction = change_direction(command_reply.commands, direction)
            elif command_reply.commands == 'M':
                exploded = move(command_reply.commands, direction, position, path, terrain, on_mine, exploded)
                print(exploded)
            elif command_reply.commands == 'D':
                if on_mine:
                    on_mine = False
                    terrain[position[0]][position[1]] = '0'

                    # GetMineNum call
                    mine_request = rover_pb2.MineNumRequest(mine_number=mine_num)
                    mine_reply = stub.GetMineNum(mine_request)

                    # RabbitMQ Deminer Call
                    rabbit_channel.queue_declare(queue='demine_queue')

                    rabbit_channel.basic_publish(exchange='',
                                                 routing_key='demine_queue',
                                                 body=f'{mine_reply.mine}%{mine_num}%{position[1]}%{position[0]}')
                    mine_num += 1
                    print("Sent mine details")

                    # Decrypt
                    # current_pin = decrypt_mine(mine_reply.mine)
                    # pins.append(current_pin)
                    # mine_num += 1

                    # SharePIN call
                    # share_request = rover_pb2.ShareRequest(pin=current_pin)
                    # share_reply = stub.SharePIN(share_request)
                    # print(share_reply.message)
                    print("DISARM")
                else:
                    print("DIG")

        print(path)
        connection.close()

        # Success call
        if exploded:
            success_request = rover_pb2.SuccessRequest(message="Failed")
            success_reply = stub.Success(success_request)
        else:
            success_request = rover_pb2.SuccessRequest(message="Success")
            success_reply = stub.Success(success_request)
        print(success_reply.message)


def change_direction(current_move, direction):
    if current_move == 'R':
        if direction == 270:
            direction = 0
        else:
            direction += 90
    elif current_move == 'L':
        if direction == 0:
            direction = 270
        else:
            direction -= 90

    if direction == 360:
        direction = 0

    return direction


def move(current_move, direction, position, path, terrain, on_mine, exploded):
    if current_move == 'M' and not exploded:
        if not on_mine:
            if direction == 0:
                position[0] = position[0] - 1
                if position[0] < 0:
                    position[0] = 0
                path[position[0]][position[1]] = '*'
                print("UP")
                return False
            elif direction == 90:
                position[1] = position[1] + 1
                if position[1] >= len(terrain[0]):
                    position[1] = position[1] - 1
                path[position[0]][position[1]] = '*'
                print("RIGHT")
                return False
            elif direction == 180:
                position[0] = position[0] + 1
                if position[0] >= len(terrain):
                    position[0] = position[0] - 1
                path[position[0]][position[1]] = '*'
                print("DOWN")
                return False
            elif direction == 270:
                position[1] = position[1] - 1
                if position[1] < 0:
                    position[1] = 0
                path[position[0]][position[1]] = '*'
                print("LEFT")
                return False
        else:
            path[position[0]][position[1]] = 'X'
            return True
    else:
        return True


# def decrypt_mine(mines):
#     pin = 0
#     while not hashlib.sha256(f'{pin}{mines}'.encode()).hexdigest().startswith("000000"):
#         pin += 1
#     print(hashlib.sha256(f'{pin}{mines}'.encode()).hexdigest())
#     # pins.append(pin)
#     # print(pins)
#     return pin


if __name__ == '__main__':
    run()
