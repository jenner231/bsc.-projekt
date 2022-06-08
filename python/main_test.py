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
import logging
from threading import Timer
from random import randint, choice

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
def get_cpu_temp():
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
node = sx126x.sx126x(serial_num = "/dev/ttyS0",freq=868,addr=n_addr,ack_info=(0,0),power=13,rssi=True,air_speed=2400,relay=False)


def heartbeat():
    seperate = ","
    #print("heartbeat 1")
    #node.reachable_dev.clear()
    #send data with ack id, wait for answer, if we get answer, note addr of answering node
    offset_frequence = int(18)
    ack_id = 0
    timer = datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")
    # the sending message format
    #
    #         receiving node              receiving node           receiving node             own high 8bit            own low 8bit              own
    #         high 8bit address           low 8bit address         frequency                  address                  address                   frequency
    #data = bytes([255]) + bytes([255]) + bytes([18]) + bytes([255]) + bytes([255]) + bytes([12]) + "CPU Temperature:".encode()+str(get_cpu_temp()).encode()+" C".encode()
    data = bytes([int(65535)>>8]) + bytes([int(65535)&0xff]) + bytes([offset_frequence]) + str(seperate).encode() + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + str(seperate).encode() + str(ack_id).encode() + str(seperate).encode() + str(timer).encode() + str(seperate).encode()
    #print(data)
    node.send(data)
    node.all_icr += 1
    node.hb_icr += 1
    logger_all.info('Total number of messages %d', node.all_icr)
    logger_hb.info("Number of hearbeat messages " + str(node.hb_icr))
    print("We sent our heartbeat out")
    sys.stdout.flush()
    
   #await asyncio.sleep(1)

#
def request_cpu_data():
    #print("req check 1")
    #####Start out checking if we have nodes that we haven't heard from in a while
    node.compare_time()
    ###choice chooses a random i in the range 1-max number of nodes but excludes its own address
    end_node = choice([i for i in range(1,node.number_of_nodes+1) if i not in [node.addr]])
    #print(end_node)
    seperate = ","
    in_reach = False

    path = node.addr
    ack_id = 1
    #print("check2")
    timer = datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")
    #print("checkpoint 3")
        #await asyncio.sleep(10)
        #global timer_task
        #global seconds
        
        # broadcast a request to end_node for it's "sensor" data, here, cpu temp
        #####We seperate with commas so its easier to decode which on the other end
    for i in node.reachable_dev:
        #print(i[0])
        n_id = int(i[0])
        if n_id == end_node:
            data = bytes([int(end_node)>>8]) + bytes([int(end_node)&0xff]) + bytes([18]) + str(seperate).encode() + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + str(seperate).encode() + str(ack_id).encode() + str(seperate).encode() + str(end_node).encode() + str(seperate).encode() + str(path).encode() + str(seperate).encode() + str(timer).encode() + str(seperate).encode()
            in_reach = True
    if not in_reach:
        data = bytes([255]) + bytes([255]) + bytes([18]) + str(seperate).encode() + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + str(seperate).encode() + str(ack_id).encode() + str(seperate).encode() + str(end_node).encode() + str(seperate).encode() + str(path).encode() + str(seperate).encode() + str(timer).encode() + str(seperate).encode()
    node.send(data)
    node.all_icr += 1
    node.req_icr += 1
    logger_all.info("Total number of messages %d", node.all_icr)
    logger_req.info("Number of request data messages " + str(node.req_icr))
    print("We requested data from: " + str(end_node))
    node.end_node = str(end_node)
    sys.stdout.flush()
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

def send_ack():
    if node.send_ack == True:

        seperate = ","
        #print("Send ack check 1")

        #node.reachable_dev.clear()
    #  send data with ack id, wait for answer, if we get answer, note addr of answering node
        offset_frequence = 18
        ack_id = 3
        ack_inf = node.get_ack()
        path = ack_inf[0]
        print(node.ack_info)

        if len(path) == 1:
            #####ack_inf[1]here is end_node set in ret_data function in sx126x
            send_to = int(ack_inf[1])
            print(send_to)

            data = bytes([int(send_to)>>8]) + bytes([int(send_to)&0xff]) + bytes([offset_frequence]) + str(seperate).encode() + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + str(seperate).encode() + str(ack_id).encode() + str(seperate).encode()

        else:
            print(path)
            send_to = int(path[1])
            #print("Send ack check xxxxx")
            path = path[1:]
            end_node = ack_inf[1]
            data = bytes([int(send_to)>>8]) + bytes([int(send_to)&0xff]) + bytes([offset_frequence]) + str(seperate).encode() + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + str(seperate).encode() + str(ack_id).encode() + str(seperate).encode() + str(path).encode() + str(seperate).encode() + str(end_node).encode() + str(seperate).encode()

        #print("Send ack check 2")

        #timer = datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")
        # the sending message format
        #
        #         receiving node              receiving node           receiving node             own high 8bit            own low 8bit              own
        #         high 8bit address           low 8bit address         frequency                  address                  address                   frequency
        #data = bytes([255]) + bytes([255]) + bytes([18]) + bytes([255]) + bytes([255]) + bytes([12]) + "CPU Temperature:".encode()+str(get_cpu_temp()).encode()+" C".encode()
        #data = bytes([int(send_to)>>8]) + bytes([int(send_to)&0xff]) + bytes([offset_frequence]) + str(seperate).encode() + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + str(seperate).encode() + str(ack_id).encode() + str(seperate).encode() + str(path).encode() + str(seperate).encode()
        node.send(data)
        node.all_icr += 1
        node.ack_icr += 1
        logger_all.info("Total number of messages %d", node.all_icr)
        logger_ack.info("Number of send ack messages " + str(node.ack_icr))
        print("We succesfully sent the ack message to the next hop in the path: " +str(ack_inf[1]))
        #####reset ack_info
        node.ack_info = (0,0)
        node.send_ack = False
        sys.stdout.flush()
        #await asyncio.sleep(1)


def cancel_cpu(cont):
    timer = 0
    max_time = 10

    while cont:
        print(timer)
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            if sys.stdin.read(1) == '\x63':
                print('\x1b[1A', end='\r')
                print(" " * 100)
                print('\x1b[1A', end='\r')
                cont = False
                print("Stopped sending data")
                return cont
        if max_time < timer:
            return cont
        else:
            timer = timer + 0.1
            time.sleep(0.1)


#TODO: Look at this function?
def forward_ack():
    #####check if we have received the requested data, if yes then send ack to end_node
    if node.forward_ack == True:
        #print("forwards_ack check 1")
        seperate = ","
        end_node = node.ack_info[1]
        #rand = float((random.randrange(0, 50, 3)) / 10)
        #await asyncio.sleep(rand)
        #print("forward_ack check 2")
        offset_frequence = 18
        ack_id = 3
        path = node.ack_info[0]
        #print(node.ack_info)
        if len(path) == 1:
            #print("forward_ack check path length 1")
            send_to = end_node
            #print("forward_ack check 2 path length 1")
            #print(send_to)
            #####ack_inf[1]here is end_node set in ret_data function in sx126x
            data = bytes([int(send_to) >> 8]) + bytes([int(send_to) & 0xff]) + bytes([offset_frequence]) + str(
                seperate).encode() + bytes([node.addr >> 8]) + bytes([node.addr & 0xff]) + bytes(
                [node.offset_freq]) + str(seperate).encode() + str(ack_id).encode() + str(seperate).encode()

        else:
            #print("forward_ack check path length more than 1")
            #print(path)
            send_to = int(path[1])
            #print("forward_ack check path length more than 2")
            path = path[1:]
            #print("forward_ack check path length more than 3")
            data = bytes([int(send_to) >> 8]) + bytes([int(send_to) & 0xff]) + bytes([offset_frequence]) + str(
                seperate).encode() + bytes([node.addr >> 8]) + bytes([node.addr & 0xff]) + bytes(
                [node.offset_freq]) + str(seperate).encode() + str(ack_id).encode() + str(seperate).encode() + str(
                path).encode() + str(seperate).encode() + str(end_node).encode() + str(seperate).encode()
            #print("forward_ack check path length more than 4")
        #print("forward_ack check 4")
        node.send(data)
        node.all_icr += 1
        node.fack_icr += 1
        logger_all.info("Total number of messages %d", node.all_icr)
        logger_fack.info("Number of forward ack messages " + str(node.fack_icr))
        #print(data)
        print("We successfully forwarded the acknowledgement message to the next hop in the path.")
        node.forward_ack = False
        sys.stdout.flush()

def ack_wait():
    #####This function is kinda dangerous if multiple nodes can send at the same time or in short succession as it allows the backup_path to be modified while node is still waiting for an acknowledgement.
    if node.wait_ack == True:

        datetimer = datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")
        clock = datetime.datetime.strptime(datetimer, '%d-%m-%y %H:%M:%S')
        current_m = int(clock.strftime("%M")) * 60
        current_s = int(clock.strftime("%S"))
        current_time = current_m + current_s

        add_delay = len(node.backup_path) + 10

        if (node.response_time + add_delay) < current_time:
            ####this line is what makes this function work. When we set node.path to the value of backup_path we "fill" path again, which allows us to enter the resp_data() function again.
            ####As it takes node.path as a boolean where it returns false if empty.
            node.path = node.backup_path
            node.wait_ack = False
            print("We did not receive the ack message")

        elif node.got_ack == True:
            node.backup_path = ""
            node.wait_ack = False
            print("ack message received succesfully")


            node.got_ack = False
        else:
            pass

def sleep_func():
        rand = float((random.randrange(0, 50, 3)) / 10)
        time.sleep(rand)

def for_mes():
    if(node.forward != 0):
        sleep_func()
        #print("for_mes 1")
        seperate = ","
        in_reach = False
        #####Just setting variables for readability. We set forward in our chechk_message function in sx126x
        ack_id = node.forward[0]
        end_node = node.forward[1]
        path = node.forward[2]
        timer = node.forward[3]
        #####check neighbours to see if we can send directly.
        for i in node.reachable_dev:
            if int(i[0]) == end_node:
                data = bytes([int(end_node)>>8]) + bytes([int(end_node)&0xff]) + bytes([18]) + str(seperate).encode() + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + str(seperate).encode() + str(ack_id).encode() + str(seperate).encode() + str(end_node).encode() + str(seperate).encode() + str(path).encode() + str(seperate).encode() + str(timer).encode() + str(seperate).encode()
                in_reach = True
        if not in_reach:
            data = bytes([255]) + bytes([255]) + bytes([18]) + str(seperate).encode() + bytes([255]) + bytes([255]) + bytes([18]) + str(seperate).encode() + str(ack_id).encode() + str(seperate).encode() + str(end_node).encode() + str(seperate).encode() + str(path).encode() + str(seperate).encode() + str(timer).encode() + str(seperate).encode()
        node.send(data)
        node.all_icr += 1
        node.for_icr += 1
        logger_all.info("Total number of messages %d", node.all_icr)
        logger_for.info("Number of forarded data messages " + str(node.for_icr))
        #print(data)
        print("We were not the requested node, successfully forwarded the request to my neighbours(or if i had the node in my cache, only it)")
        node.forward = 0
        sys.stdout.flush()
    else:
        pass


def resp_data():
    ####if we have something in our path array, basically says if len(node.path) not empty
    if node.path:
        #await sleep_func()
        #print("resp_data 1")
        seperate = ","
        send_to = int(node.path[-1])
        #####back_path is used in ack_wait(). response_time is also used in ack_wait and stores the time we sent the message, so we know when the ack message times out
        #####We only enter the statement if we dont have anything in backup_path already.
        #print(len(node.backup_path))
        if len(node.backup_path) == 0:
            node.backup_path = node.path
            timer = datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")
            sent_message_timer = datetime.datetime.strptime(timer, '%d-%m-%y %H:%M:%S')
            old_m = int(sent_message_timer.strftime("%M")) * 60
            old_s = int(sent_message_timer.strftime("%S"))
            node.response_time = old_m + old_s
            node.wait_ack = True

        temp = str("CPU Temperature:"+str(get_cpu_temp())+ " C")

        if len(node.path) == 1:
            path = ""
        else:
            path = node.path[0:-1]  
        offset_frequence = 18
        ack_id = 2
    
        data = bytes([int(send_to)>>8]) + bytes([int(send_to)&0xff]) + bytes([offset_frequence]) + str(seperate).encode() + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + str(seperate).encode() + str(ack_id).encode() + str(seperate).encode() + str(path).encode() + str(seperate).encode() + str(temp).encode() + str(seperate).encode() + str(node.backup_path).encode() + str(seperate).encode()
        node.send(data)
        node.all_icr += 1
        node.resp_icr += 1
        logger_all.info("Total number of messages %d", node.all_icr)
        logger_resp.info("Number of respond data messages " + str(node.resp_icr))
        print("we send the response, waiting for ack")
        #####Clean the node's path after sending the message
        node.backup_path = ""
        node.path = ""
        sys.stdout.flush()
    else:
        pass


def ret_data():
    ####This function is differnt than resp_data() in the way that this is function relays the message between intermediate nodes, while resp_data() only handles
    ####the initial response. (This is the general function and resp_data() is the base case.)
    if node.data[0]:
        #await sleep_func()
        #print("sender ret data 1")
        seperate = ","
        payload = node.data[0]
        path = node.data[1]
        backup_path = node.data[2]
        #print("sender ret data 2")
        send_to = int(path[-1])

        if len(path) == 1:
            path = ""
        else:
            path = path[0:-1]

        offset_frequence = 18
        ack_id = 2

        #####node.get_ack[1] is the sender address stored in the get_ack function       
        data = bytes([int(send_to)>>8]) + bytes([int(send_to)&0xff]) + bytes([offset_frequence]) + str(seperate).encode() + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + str(seperate).encode() + str(ack_id).encode() + str(seperate).encode() + str(path).encode() + str(seperate).encode() + str(payload).encode() + str(seperate).encode() + str(backup_path).encode() + str(seperate).encode()
        node.send(data)

        ##### increment counter for number of messages sent and number of type of message sent
        node.all_icr += 1
        node.ret_icr += 1
        logger_all.info("Total number of messages %d", node.all_icr)
        logger_ret.info("Number of return data messages " + str(node.ret_icr))

        #print(data)
        print("Forwarding return data to next hop")
        #####Clean the node's data after sending the message
        node.data = ("","")
        sys.stdout.flush()

    #####https://stackoverflow.com/questions/11232230/logging-to-two-files-with-different-settings reference
def setup_logger(logger_name, log_file, level=logging.INFO):
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(message)s')
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setFormatter(formatter)
    #streamHandler = logging.StreamHandler()
    #streamHandler.setFormatter(formatter)



    l.setLevel(level)
    l.addHandler(fileHandler)
    #l.addHandler(streamHandler)


def async_main():
    #print("Press \033[1;32mEsc\033[0m to exit")
    #print("Press \033[1;32mi\033[0m   to send")
    #print("Press \033[1;32ms\033[0m   to send cpu temperature every 10 seconds")
    ##### Loggers to keep count of number of messages, and number of each type of messages sent
    print("Mesh Network Prototype: Start")
    setup_logger('log_all', "log_all.txt")
    setup_logger('log_ack', "log_ack.txt")
    setup_logger('log_resp', "log_resp.txt")
    setup_logger('log_for', "log_for.txt")
    setup_logger('log_hb', "log_hb.txt")
    setup_logger('log_ret', "log_ret.txt")
    setup_logger('log_req', "log_req.txt")
    setup_logger('log_fack', "log_fack.txt")
    setup_logger('log_receive', "log_receive.txt")
    setup_logger('log_error', "log_error.txt")

    #print("main checkpoint 1")

    global logger_all, logger_ack, logger_fack, logger_for, logger_hb, logger_req, logger_resp, logger_ret
    #print("main checkpoint 2")
    logger_all = logging.getLogger('log_all')
    logger_ack = logging.getLogger('log_ack')
    logger_resp = logging.getLogger('log_resp')
    logger_for = logging.getLogger('log_for')
    logger_hb = logging.getLogger('log_hb')
    logger_ret = logging.getLogger('log_ret')
    logger_req = logging.getLogger('log_req')
    logger_fack = logging.getLogger('log_fack')
    logger_receive = logging.getLogger('log_receive')
    logger_error = logging.getLogger('log_error')
    #print("main checkpoint 3")



    ##### Variables in order to slot the network, determining when to heartbeat and request messages depending on number of nodes in the network
    s_timer = datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")
    timer = datetime.datetime.strptime(s_timer, '%d-%m-%y %H:%M:%S')
    m = timer.minute


    cycle = 60
    slot_start = (int(node.addr) / (node.number_of_nodes + 1)) * cycle
    slot_idle = slot_start * (1 / (node.number_of_nodes + 1))
    slot_size = cycle / (node.number_of_nodes + 1)
    slot_end = slot_start + slot_size - slot_idle

    hb_start = 0
    hb_end = ((1 / (node.number_of_nodes + 1)) * cycle) - (((1 / (node.number_of_nodes + 1)) * cycle) / (node.number_of_nodes + 1))
    hb_slot_size = (hb_end - hb_start) / (node.number_of_nodes)
    hb_slot_start = hb_start + (int(node.addr) - 1) * hb_slot_size
    hb_next_start = hb_start + int(node.addr) * hb_slot_size

    while True:
        c_timer = datetime.datetime.now()
        c_t = float(c_timer.second) + (c_timer.microsecond / 1000000)
        new_m = c_timer.minute
        #####if statement to reset cycle each minute
        if new_m > m:
            node.has_sent_hb = False
            node.has_sent_mes = False
            #####We need to reset this variable in case the last node to send last cycle tries to send as the first node this cycle.
            node.store_received_requests = 0
            m = new_m
        elif new_m == 0 and m == 59:
            node.has_sent_hb = False
            node.has_sent_mes = False
            node.store_received_requests = 0
            m = new_m 


        #####Mac protocol to slot each node into timeslots and give a slot to hearbeats, which is then also split into slots.
        if c_t > hb_slot_start and c_t < hb_next_start and (not node.has_sent_hb):
            heartbeat()
            node.has_sent_hb = True
        
        if c_t > slot_start and c_t < slot_end and (not node.has_sent_mes):
            request_cpu_data()
            node.has_sent_mes = True






        # if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
        #     c = sys.stdin.read(1)
        #     # dectect key Esc
        #     if c == '\x1b': break
        #     # dectect key i
        #     if c == '\x69':
        #         print("Checkpoint1: In main loop, pressed i")
        #         #task_req = asyncio.create_task(request_cpu_data())
        #         #await task_req
        #         task_heartbeat = asyncio.create_task(heartbeat())
        #         #task_deal = asyncio.create_task(send_deal())
        #         #await task_deal()
        #         await task_heartbeat
        #     # dectect key s
        #     if c == '\x73':
        #         print("Press \033[1;32mc\033[0m   to exit the send task")
        #         #timer_task = Timer(seconds, send_cpu_continue)
        #         #timer_task.start()
        #         #####Create the task to send "sensor" data to nearby devices
        #         #cont = True
        #         #while cont == True:

        #         #cont = await cancel_cpu(cont)
        #         #press c to cancel
                
        #             #await asyncio.sleep(10) 
        node.receive(logger_receive, logger_error)
        # if timer != 0:
        #     task_return = asyncio.create_task(return_ack())
        #     await task_return
        #     if timer + str('00:00:05', "%H:%M:%S") < datetime.now().time():
        #         timer = 0
        # else: 
        #     pass
        for_mes()
        resp_data()
        ret_data()

        send_ack()
        forward_ack()
        ack_wait()
        sys.stdout.flush()

        #wait asyncio.sleep(0.01)

        # timer,send messages automatically

try:
    #seconds = 10
    async_main()
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



