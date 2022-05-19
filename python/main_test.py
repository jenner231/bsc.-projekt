#!/usr/bin/python
# -*- coding: UTF-8 -*-

#
#    this is an UART-LoRa device and thers is an firmware on Module
#    users can transfer or receive the data directly by UART and dont
#    need to set parameters like coderate,spread factor,etc.
#    |============================================ |
#    |   It does not suport LoRaWAN protocol !!!   |
#    | ============================================|
#   
#    This script is mainly for Raspberry Pi 3B+, 4B, and Zero series
#    Since PC/Laptop does not have GPIO to control HAT, it should be configured by
#    GUI and while setting the jumpers, 
#    Please refer to another script pc_main.py
#

from encodings import utf_8
from multiprocessing import cpu_count
from pickle import TRUE
from ssl import ALERT_DESCRIPTION_UNKNOWN_PSK_IDENTITY
import sys
import sx126x
import threading
import time
import select
import termios
import asyncio
import tty
import datetime
import random
from threading import Timer

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())


#####Importing node_id from a seperate folder not including in git, so we can keep pulling without defaulting back to std node_id
sys.path.insert(1, '/home/pi/address')
import address
n_addr = address.node.n_address
sys.path.insert(1, '/home/bsc.-projekt/python')


#
#    Need to disable the serial login shell and have to enable serial interface 
#    command `sudo raspi-config`
#    More details: see https://github.com/MithunHub/LoRa/blob/main/Basic%20Instruction.md
#
#    When the LoRaHAT is attached to RPi, the M0 and M1 jumpers of HAT should be removed.
#


#    The following is to obtain the temprature of the RPi CPU 
async def get_cpu_temp():
    tempFile = open( "/sys/class/thermal/thermal_zone0/temp" )
    cpu_temp = tempFile.read()
    tempFile.close()
    return float(cpu_temp)/1000

#   serial_num
#       PiZero, Pi3B+, and Pi4B use "/dev/ttyS0"
#
#    Frequency is [850 to 930], or [410 to 493] MHz
#
#    address is 0 to 65535
#        under the same frequence,if set 65535,the node can receive 
#        messages from another node of address is 0 to 65534 and similarly,
#        the address 0 to 65534 of node can receive messages while 
#        the another note of address is 65535 sends.
#        otherwise two node must be same the address and frequence
#
#    The tramsmit power is {10, 13, 17, and 22} dBm
#
#    RSSI (receive signal strength indicator) is {True or False}
#        It will print the RSSI value when it receives each message
#

# node = sx126x.sx126x(serial_num = "/dev/ttyS0",freq=433,addr=0,power=22,rssi=False,air_speed=2400,relay=False)
node = sx126x.sx126x(serial_num = "/dev/ttyS0",freq=868,addr=n_addr,ack_info=(0,0),power=22,rssi=True,air_speed=2400,relay=False)

async def send_deal():
    #####Added the second input requirement of node id (also mentioned as 0 in line 72)
    get_rec = ""
    print("")
    print("input a string such as \033[1;32m0,868,Hello World\033[0m,it will send `Hello World` to lora node device of address 0 with frequncy 868M ")
    print("please input and press Enter key:",end='',flush=True)
    ack_id = 1
    while True:
        rec = sys.stdin.read(1)
        if rec != None:
            if rec == '\x0a': break
            get_rec += rec
            sys.stdout.write(rec)
            sys.stdout.flush()

    get_t = get_rec.split(",")

    offset_frequence = int(get_t[1])-(850 if int(get_t[1])>850 else 410)
    #####Added the node id to the data variable, both in receiving node and own node.
    #####
    # the sending message format
    #
    #         receiving node              receiving node             receiving node             own high 8bit            own low 8bit                     
    #         high 8bit address           low 8bit addre             frequency                  address                  address                          own freqency            ack_id                  message payload
    data = bytes([int(get_t[0])>>8]) + bytes([int(get_t[0])&0xff]) + bytes([offset_frequence]) + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) +  str(ack_id).encode() + get_t[2].encode()

    node.send(data)
    print('\x1b[2A',end='\r')
    print(" "*200)
    print(" "*200)
    print(" "*200)
    print('\x1b[3A',end='\r')

async def request_cpu_continue():
    end_node = 3
    path = [node.addr]
    ack_id = 1
    time = datetime.datetime.now()
        #await asyncio.sleep(10)
        #global timer_task
        #global seconds
        
        # broadcast a request to end_node for it's "sensor" data, here, cpu temp
    data = bytes([255]) + bytes([255]) + bytes([18]) + bytes([255]) + bytes([255]) + bytes([12]) + str(ack_id).encode() + str(end_node).encode() + str(path).encode() + str(time).encode()
    node.send(data)
    # broadcast the cpu temperature at 868.125MHz
    #data = bytes([255]) + bytes([255]) + bytes([18]) + bytes([255]) + bytes([255]) + bytes([12]) + str(ack_id).encode() + "CPU Temperature:".encode()+str(await get_cpu_temp()).encode()+" C".encode()
    #node.send(data)
    #time.sleep(0.2)
    #rec = asyncio.create_task(send_cpu_continue())
    #await rec
    #timer_task = Timer(seconds,send_cpu_continue)
    #timer_task.start()
    #data = bytes([255]) + bytes([255]) + bytes([18]) + bytes([255]) + bytes([255]) + bytes([12]) + str(ack_id).encode() +  "CPU Temperature:".encode()+str(await get_cpu_temp()).encode()+" C".encode()
    #node.send(data)
    #time.sleep(0.2)
    #timer_task.cancel()
    
async def send_ack():
    #node.reachable_dev.clear()
  #  send data with ack id, wait for answer, if we get answer, note addr of answering node
    offset_frequence = int(18)
    ack_id = 0
    # the sending message format
    #
    #         receiving node              receiving node           receiving node             own high 8bit            own low 8bit              own
    #         high 8bit address           low 8bit address         frequency                  address                  address                   frequency
    #data = bytes([255]) + bytes([255]) + bytes([18]) + bytes([255]) + bytes([255]) + bytes([12]) + "CPU Temperature:".encode()+str(get_cpu_temp()).encode()+" C".encode()
    data = bytes([int(65535)>>8]) + bytes([int(65535)&0xff]) + bytes([offset_frequence]) + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + str(ack_id).encode()
    print(data[0])
    print(data[1])
    print(data[2])
    print(data[3])
    node.send(data)
    #await asyncio.sleep(1)

async def cancel_cpu(cont):
    time = 0
    max_time = 10

    while cont:
        print(time)
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            if sys.stdin.read(1) == '\x63':
                print('\x1b[1A', end='\r')
                print(" " * 100)
                print('\x1b[1A', end='\r')
                cont = False
                print("Stopped sending data")
                return cont
        if max_time < time:
            return cont
        else:
            time = time + 0.1
            print(time)
            await asyncio.sleep(0.1)

async def return_ack():
        #####check wether we've gotten a heartbeat each loop
        #####49 == 1 in ascii
    info = node.get_ack()
    if info[0] == 49:
        print(time.time()*1000)
        rand = float((random.randrange(0, 50, 3)) / 10)
        print(time.time()*1000)
        await asyncio.sleep(rand)
        print("checkpoint1 ")
        offset_frequence = 18
        ack_id = 2

        #####node.get_ack[1] is the sender address stored in the get_ack function
        data = bytes([int(info[1])>>8]) + bytes([int(info[1])&0xff]) + bytes([offset_frequence]) + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + str(ack_id).encode()
        print("checkpoint2")
        node.send(data)
    else:
        pass

async def for_mes():
    if(node.forward != 0):
        #####Just setting variables for readability. We set forward in our chechk_message function in sx126x
        ack_id = node.forward[0]
        end_node = node.forward[1]
        path = node.forward[2]
        time = node.forward[3]
        data = bytes([255]) + bytes([255]) + bytes([18]) + bytes([255]) + bytes([255]) + bytes([12]) + str(ack_id).encode() + str(end_node).encode() + str(path).encode() + str(time).encode()
        node.send(data)
        node.forward = 0
    else:
        pass

async def ret_mes():
    ####if we have something in our path array, basically says if len(node.path) not empty
    if node.path:
        send_to = node.path[-1]
        temp = str("CPU Temperature:"+str(get_cpu_temp())+ " C")
        if len(node.path) == 1:
            path = []
        else:
            path = node.path[0:-2]

        offset_frequence = 18
        ack_id = 2
        if node.data:
            temp = node.data
            node.data = []


        #####node.get_ack[1] is the sender address stored in the get_ack function
        data = bytes([int(send_to)>>8]) + bytes([int(send_to)&0xff]) + bytes([offset_frequence]) + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + str(ack_id).encode() + str(path).encode() + str(temp).encode()
        node.send(data)


                

async def async_main():
    #await asyncio.sleep(0.1)
    print("Press \033[1;32mEsc\033[0m to exit")
    print("Press \033[1;32mi\033[0m   to send")
    print("Press \033[1;32ms\033[0m   to send cpu temperature every 10 seconds")

    while True:
        timer = 0
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)
            # dectect key Esc
            if c == '\x1b': break
            # dectect key i
            if c == '\x69':
                task_fward = asyncio.create_task(for_mes())
                await task_fward
                #task_ack = asyncio.create_task(send_ack())
                #task_deal = asyncio.create_task(send_deal())
                #await send_deal()
                #await send_ack()
            # dectect key s
            if c == '\x73':
                print("Press \033[1;32mc\033[0m   to exit the send task")
                #timer_task = Timer(seconds, send_cpu_continue)
                #timer_task.start()
                #####Create the task to send "sensor" data to nearby devices
                
                while cont == True:
                    cpu = asyncio.create_task(send_cpu_continue())
                    await cpu
                    cont = await cancel_cpu(cont)
                    #press c to cancel
                
                    #await asyncio.sleep(10) 

            sys.stdout.flush()
        node.receive()
        if timer != 0:
            task_return = asyncio.create_task(return_ack())
            await task_return
            if timer + str('00:00:05', "%H:%M:%S") < datetime.now().time():
                timer = 0
        else: 
            pass


        #wait asyncio.sleep(0.01)

        # timer,send messages automatically

try:
    #seconds = 10
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main())
    #asyncio.run(async_main())
except:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    # print('\x1b[2A',end='\r')
    # print(" "*100)
    # print(" "*100)
    # print('\x1b[2A',end='\r')

termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
# print('\x1b[2A',end='\r')
# print(" "*100)
# print(" "*100)
# print('\x1b[2A',end='\r')



