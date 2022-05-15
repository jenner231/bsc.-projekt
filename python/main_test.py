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
import sys
import sx126x
import threading
import time
import select
import termios
import asyncio
import tty
import datetime
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
node = sx126x.sx126x(serial_num = "/dev/ttyS0",freq=868,addr=n_addr,power=22,rssi=True,air_speed=2400,relay=False)

async def send_deal():
    #####Added the second input requirement of node id (also mentioned as 0 in line 72)
    get_rec = ""
    print("")
    print("input a string such as \033[1;32m0,868,Hello World\033[0m,it will send `Hello World` to lora node device of address 0 with frequncy 868M ")
    print("please input and press Enter key:",end='',flush=True)
    ack_id = 0
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

async def send_cpu_continue(continue_or_not = True):
    ack_id = 0
    if continue_or_not:
        #await asyncio.sleep(10)
        #global timer_task
        #global seconds
        
        # boarcast the cpu temperature at 868.125MHz
        
        data = bytes([255]) + bytes([255]) + bytes([18]) + bytes([255]) + bytes([255]) + bytes([12]) + str(ack_id).encode() + "CPU Temperature:".encode()+str(await get_cpu_temp()).encode()+" C".encode()
        node.send(data)
        #time.sleep(0.2)
        #rec = asyncio.create_task(send_cpu_continue())
        #await rec
        #timer_task = Timer(seconds,send_cpu_continue)
        #timer_task.start()
    else:
        data = bytes([255]) + bytes([255]) + bytes([18]) + bytes([255]) + bytes([255]) + bytes([12]) + str(ack_id).encode() +  "CPU Temperature:".encode()+str(await get_cpu_temp()).encode()+" C".encode()
        node.send(data)
        #time.sleep(0.2)
        #timer_task.cancel()
        pass
async def send_ack():
  #  send data with ack id, wait for answer, if we get answer, note addr of answering node
    offset_frequence = int(18)
    ack_id = 1
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
    await asyncio.sleep(1)

async def cancel_cpu(cont):
    time = 0
    cancel_cont = cont
    print("checkpoint 1")
    #####We need to differentiate between the two continue variables, as if we dont press c, after 10 seconds we want to return true for the outer loop, but false for the cancel_cpu loop
    ##### But if we do press c, we want to cancel both
    while cancel_cont:
        print(time)
        #if sys.stdin.read(1) == '\x63':
         #   print('\x1b[1A', end='\r')
          #  print(" " * 100)
           # print('\x1b[1A', end='\r')
            #cont = False
            #cancel_cont = cont
            #return cont
        if 1 < time:
            cancel_cont = False
            return cont
        else:
            cancel_cont = True
            time = time + 0.1
            print(time)
            time.sleep(0.1)

async def async_main():
    await asyncio.sleep(0.1)
    print("Press \033[1;32mEsc\033[0m to exit")
    print("Press \033[1;32mi\033[0m   to send")
    print("Press \033[1;32ms\033[0m   to send cpu temperature every 10 seconds")

    while True:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1)
            # dectect key Esc
            if c == '\x1b': break
            # dectect key i
            if c == '\x69':
                #task_ack = asyncio.create_task(send_ack())
                task_deal = asyncio.create_task(send_deal())
                #await send_deal()
                await send_ack()
            # dectect key s
            if c == '\x73':
                print("Press \033[1;32mc\033[0m   to exit the send task")
                #timer_task = Timer(seconds, send_cpu_continue)
                #timer_task.start()
                #####Create the task to send "sensor" data to nearby devices
                
                cont = True
                while cont == True:
                    cpu = asyncio.create_task(send_cpu_continue())
                    await cpu
                    cont2 = await cancel_cpu(cont)
                    cont = cont2
                    print("checkpoint 2")
                    #press c to cancel
                
                    #await asyncio.sleep(10) 

            sys.stdout.flush()
        node.receive()
        await asyncio.sleep(0.01)

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



