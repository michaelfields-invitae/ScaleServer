from mettler_toledo_device import MettlerToledoDevice
import zmq
import time
import clr
clr.AddReference("C:\\Program Files (x86)\\Tecan\\FluentControl\\Tecan.VisionX.API.V2.dll")
from Tecan.VisionX.API.V2 import FluentControl
from datetime import datetime


# Timeout based on serial_interface.py max_read_attempts
# this reads every 0.1 seconds, and defaults to 100, changed to 300
def send_request_from_client(cmd, target):
    cmd_dict = {'S': 2,
                'SI': 2,
                'T': 2,
                'Z': 0}

    try:
        cmd_response = dev._send_request_get_response(cmd)
        raw_weights.append(("Command response: ", cmd_response))
        stable_weight = cmd_response[cmd_dict[cmd]]
        run.SetVariableValue("stable_weight", stable_weight)
        raw_weights.append((stable_weight, cmd, target))
        print(f'Command response: {cmd_response}')
    except Exception as e:
        stable_weight = "Error"
        raw_weights.append(("Error from cmd:", cmd, cmd_dict[cmd], e))
        print("Error, inside exception: ")
        print(e)

    return str(stable_weight)

# Connect to fluent control
FC_instance = FluentControl()
FC_instance.StartOrAttach()
run = FC_instance.GetRuntime()
print("Connected to Fluent Control")

# Connect to scale
dev = MettlerToledoDevice(port='COM7') # Windows specific port
print("Connected to scale on COM7.")

# Open server
context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")
print("Serving port 5555.")

# Main control loop
# Scale command dictionary and return argument value
cmd = None
raw_weights = []
time_elapsed = 0

filename = r'C:\users\Tecan\Desktop\weightoutputs_' + str(datetime.now().strftime("%m_%d_%Y_%H_%M")) + '.txt'
with open(filename, "w+") as file:
    while True:
        try:
            weight = dev._send_request_get_response('SI')
            raw_weights.append(weight[2])

            #  Check for next request from client
            try:
                message = socket.recv(flags=zmq.NOBLOCK)  # Throws error if no cmd received
                print("Received request: %s" % message)
                msg = message.decode("utf-8")
                msg_array = msg.split(",")
                cmd = msg_array[0]
                target = msg_array[1]
                print(f'cmd: {cmd}, target: {target}')
                if cmd == "stop":
                    socket.send(b"Received")
                    break
                elif cmd:
                    stable_weight = send_request_from_client(cmd, target)
                    socket.send_string(stable_weight)

            except zmq.Again as e:
                print(f'Listening ... {time_elapsed}')
        except Exception as e:
            pass

        time.sleep(0.25)
        time_elapsed += 0.25

        file.write(str(weight))
print("Exited control loop.")

backupfile = r'C:\users\Tecan\Desktop\weightoutputs_backup_' + str(datetime.now().strftime("%m_%d_%Y_%H_%M")) + '.txt'
f = open(backupfile, "w+")  # open(r"C:\users\Tecan\Desktop\weightoutputs.txt", "w+")
f.write(str(raw_weights))
f.close()
