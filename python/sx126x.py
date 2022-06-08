# This file is used for LoRa and Raspberry pi4B related issues 

from array import array
from ctypes import sizeof
from curses import raw
import RPi.GPIO as GPIO
import serial
import time
import datetime
import sys
import logging
from encodings import utf_8
import number_of_nodes


class sx126x:
    ##importing the node library to manually set node id on each node without overwriting from github pulls
    sys.path.insert(1, '/home/pi/address')
    import address
    n_addr = address.node.n_address
    sys.path.insert(1, '/home/bsc.-projekt/python')
    M0 = 22
    M1 = 27
    # if the header is 0xC0, then the LoRa register settings dont lost when it poweroff, and 0xC2 will be lost. 
    # cfg_reg = [0xC0,0x00,0x09,0x00,0x00,0x00,0x62,0x00,0x17,0x43,0x00,0x00]
    cfg_reg = [0xC2,0x00,0x09,0x00,0x00,0x00,0x62,0x00,0x12,0x43,0x00,0x00]
    get_reg = bytes(12)
    rssi = False
    addr = 0
    ###This is set manually, probably should be set from a 
    number_of_nodes = number_of_nodes.non.number_of_nodes
    timeslot = 0
    serial_n = ""
    addr_temp = 0
    #### reachable_dev tuple for heartbeat on form (node_id, time)
    reachable_dev = []
    ack_info = (0,0)
    received_time = (0, 0)
    response_time = 0
    path = ""
    store_received_requests = 0
    #####Backup path is used if we dont received the acknowledgement message after responding with our data.
    backup_path = ""
    #### Both also includes path, but we can't use path as path variable is used as a boolean to enter a function in the main file.
    forward = 0
    data = ("", "", "")
    #####Used for logging purposes
    end_node = ""
    #####Bools used in timing
    got_ack = False
    wait_ack = False
    send_ack = False
    forward_ack = False
    has_sent_mes = False
    has_sent_hb = False

    #####Incrementers used for logging
    all_icr = 0
    ack_icr = 0
    resp_icr = 0
    for_icr = 0
    hb_icr = 0
    ret_icr = 0
    req_icr = 0
    fack_icr = 0
    receive_icr = 0
    error_icr = 0



    #
    # start frequence of two lora module
    #
    # E22-400T22S           E22-900T22S
    # 410~493MHz      or    850~930MHz
    start_freq = 850

    #
    # offset between start and end frequence of two lora module
    #
    # E22-400T22S           E22-900T22S
    # 410~493MHz      or    850~930MHz
    offset_freq = 18

    # power = 22
    # air_speed =2400

    SX126X_UART_BAUDRATE_1200 = 0x00
    SX126X_UART_BAUDRATE_2400 = 0x20
    SX126X_UART_BAUDRATE_4800 = 0x40
    SX126X_UART_BAUDRATE_9600 = 0x60
    SX126X_UART_BAUDRATE_19200 = 0x80
    SX126X_UART_BAUDRATE_38400 = 0xA0
    SX126X_UART_BAUDRATE_57600 = 0xC0
    SX126X_UART_BAUDRATE_115200 = 0xE0

    SX126X_PACKAGE_SIZE_240_BYTE = 0x00
    SX126X_PACKAGE_SIZE_128_BYTE = 0x40
    SX126X_PACKAGE_SIZE_64_BYTE = 0x80
    SX126X_PACKAGE_SIZE_32_BYTE = 0xC0

    SX126X_Power_22dBm = 0x00
    SX126X_Power_17dBm = 0x01
    SX126X_Power_13dBm = 0x02
    SX126X_Power_10dBm = 0x03


    lora_air_speed_dic = {
        1200:0x01,
        2400:0x02,
        4800:0x03,
        9600:0x04,
        19200:0x05,
        38400:0x06,
        62500:0x07
    }

    lora_power_dic = {
        22:0x00,
        17:0x01,
        13:0x02,
        10:0x03
    }

    lora_buffer_size_dic = {
        240:SX126X_PACKAGE_SIZE_240_BYTE,
        128:SX126X_PACKAGE_SIZE_128_BYTE,
        64:SX126X_PACKAGE_SIZE_64_BYTE,
        32:SX126X_PACKAGE_SIZE_32_BYTE
    }

    def __init__(self,serial_num,freq,addr,ack_info,power,rssi,air_speed=2400,\
                 net_id=0,buffer_size = 240,crypt=0,\
                 relay=False,lbt=False,wor=False):
        self.rssi = rssi
        self.addr = addr
        self.freq = freq
        self.serial_n = serial_num
        self.power = power
        self.ack_info = ack_info
        # Initial the GPIO for M0 and M1 Pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.M0,GPIO.OUT)
        GPIO.setup(self.M1,GPIO.OUT)
        GPIO.output(self.M0,GPIO.LOW)
        GPIO.output(self.M1,GPIO.HIGH)

        # The hardware UART of Pi3B+,Pi4B is /dev/ttyS0
        self.ser = serial.Serial(serial_num,9600)
        self.ser.flushInput()
        self.set(freq,addr,power,rssi,air_speed,net_id,buffer_size,crypt,relay,lbt,wor)
    def set(self,freq,addr,power,rssi,air_speed=2400,\
            net_id=0,buffer_size = 240,crypt=0,\
            relay=False,lbt=False,wor=False):
        self.send_to = addr
        self.addr = addr
        # We should pull up the M1 pin when sets the module
        GPIO.output(self.M0,GPIO.LOW)
        GPIO.output(self.M1,GPIO.HIGH)
        time.sleep(0.1)

        low_addr = addr & 0xff
        high_addr = addr >> 8 & 0xff
        net_id_temp = net_id & 0xff
        if freq > 850:
            freq_temp = freq - 850
            self.start_freq = 850
            self.offset_freq = freq_temp
        elif freq >410:
            freq_temp = freq - 410
            self.start_freq  = 410
            self.offset_freq = freq_temp
        
        air_speed_temp = self.lora_air_speed_dic.get(air_speed,None)
        # if air_speed_temp != None
        
        buffer_size_temp = self.lora_buffer_size_dic.get(buffer_size,None)
        # if air_speed_temp != None:
        
        power_temp = self.lora_power_dic.get(power,None)
        #if power_temp != None:

        if rssi:
            # enable print rssi value 
            rssi_temp = 0x80
        else:
            # disable print rssi value
            rssi_temp = 0x00        

        # get crypt
        l_crypt = crypt & 0xff
        h_crypt = crypt >> 8 & 0xff
        
        if relay==False:
            self.cfg_reg[3] = high_addr
            self.cfg_reg[4] = low_addr
            self.cfg_reg[5] = net_id_temp
            self.cfg_reg[6] = self.SX126X_UART_BAUDRATE_9600 + air_speed_temp
            # 
            # it will enable to read noise rssi value when add 0x20 as follow
            # 
            self.cfg_reg[7] = buffer_size_temp + power_temp + 0x20
            self.cfg_reg[8] = freq_temp
            #
            # it will output a packet rssi value following received message
            # when enable eighth bit with 06H register(rssi_temp = 0x80)
            #
            self.cfg_reg[9] = 0x43 + rssi_temp
            self.cfg_reg[10] = h_crypt
            self.cfg_reg[11] = l_crypt
        else:
            self.cfg_reg[3] = 0x01
            self.cfg_reg[4] = 0x02
            self.cfg_reg[5] = 0x03
            self.cfg_reg[6] = self.SX126X_UART_BAUDRATE_9600 + air_speed_temp
            # 
            # it will enable to read noise rssi value when add 0x20 as follow
            # 
            self.cfg_reg[7] = buffer_size_temp + power_temp + 0x20
            self.cfg_reg[8] = freq_temp
            #
            # it will output a packet rssi value following received message
            # when enable eighth bit with 06H register(rssi_temp = 0x80)
            #
            self.cfg_reg[9] = 0x03 + rssi_temp
            self.cfg_reg[10] = h_crypt
            self.cfg_reg[11] = l_crypt
        self.ser.flushInput()

        for i in range(2):
            self.ser.write(bytes(self.cfg_reg))
            r_buff = 0
            time.sleep(0.2)
            if self.ser.inWaiting() > 0:
                time.sleep(0.1)
                r_buff = self.ser.read(self.ser.inWaiting())
                if r_buff[0] == 0xC1:
                    pass
                    # print("parameters setting is :",end='')
                    # for i in self.cfg_reg:
                        # print(hex(i),end=' ')
                        
                    # print('\r\n')
                    # print("parameters return is  :",end='')
                    # for i in r_buff:
                        # print(hex(i),end=' ')
                    # print('\r\n')
                else:
                    pass
                    #print("parameters setting fail :",r_buff)
                break
            else:
                print("setting fail,setting again")
                self.ser.flushInput()
                time.sleep(0.2)
                print('\x1b[1A',end='\r')
                if i == 1:
                    print("setting fail,Press Esc to Exit and run again")
                    # time.sleep(2)
                    # print('\x1b[1A',end='\r')

        GPIO.output(self.M0,GPIO.LOW)
        GPIO.output(self.M1,GPIO.LOW)
        time.sleep(0.1)

    def get_settings(self):
        # the pin M1 of lora HAT must be high when enter setting mode and get parameters
        GPIO.output(M1,GPIO.HIGH)
        time.sleep(0.1)
        
        # send command to get setting parameters
        self.ser.write(bytes([0xC1,0x00,0x09]))
        if self.ser.inWaiting() > 0:
            time.sleep(0.1)
            self.get_reg = self.ser.read(self.ser.inWaiting())
        
        # check the return characters from hat and print the setting parameters
        if self.get_reg[0] == 0xC1 and self.get_reg[2] == 0x09:
            fre_temp = self.get_reg[8]
            addr_temp = self.get_reg[3] + self.get_reg[4]
            air_speed_temp = self.get_reg[6] & 0x03
            power_temp = self.get_reg[7] & 0x03
            
            print("Frequence is {0}.125MHz.",fre_temp)
            print("Node address is {0}.",addr_temp)
            print("Air speed is {0} bps"+ lora_air_speed_dic.get(None,air_speed_temp))
            print("Power is {0} dBm" + lora_power_dic.get(None,power_temp))
            GPIO.output(M1,GPIO.LOW)

#
# the data format like as following
# "node address,frequence,payload"
# "20,868,Hello World"
    def send(self,data):
        GPIO.output(self.M1,GPIO.LOW)
        GPIO.output(self.M0,GPIO.LOW)
        time.sleep(0.1)
        
        self.ser.write(data)
        # if self.rssi == True:
            # self.get_channel_rssi()
        time.sleep(0.1)

    def get_ack(self):
        return self.ack_info

    #####Function to determine wether we have seen a request for this data before. e.g if multiple nodes can reach the end node with different paths, 
    #####we only want to answer the first one
    def calc_new_message(self, time, path):
        #print("checkpoint calc message 1")
        #print(type(datetime.datetime.now()))
        #print(time)
        #print(type(time))
        dateT = datetime.datetime.strptime(time, '%d-%m-%y %H:%M:%S')
        #print(dateT)
        m = dateT.strftime("%M") * 60 
        s = dateT.strftime("%S")
        #print("checkpoint calc message 2")
        #####See if we've already received a time from the same address set time to the time received, else set time to 0 for next statement
        #####Here it's okay to only check path[0] as we've already made sure in check_message() func, that we haven't visited a node twice.
        if self.received_time[0] != 0 and self.received_time[1] == path[0]:
            c_m, c_s = self.received_time.strftime("%M"), self.received_time.strftime("%S")
        else:
            c_m, c_s = 0, 0
        #####if we have a message with the same origin from the same time, we return false, else True
        if (int(m) + int(s)) == (int(c_m) + int(c_s)) and path[0] == self.path[0]:
            #print("We have seen the message from node id "+ self.path[0] + "before")
            return False
        else:
            return True

    def check_message(self, r_buff):
        #print("check message checkpoint 1")
        visited = False
        #####Check we have visited this not before to avoid infinite loop when flooding the network in broadcasts
        path = r_buff[4]
        ####must remove \\x to convert from string to int 
        sender = r_buff[1].split("\\x") 
        for i in path:
            val = int(i)
            if self.addr == val:
                                                            ##Path[-1] returns the last element in path, which in turn is the sender of the message this node received
                print("We have seen the message from node id "+ str(path[-1]) + " before")
                visited = True

        ####if we're the end node, go in here (this pseudo calls resp_data() by setting its bool in path)
        if int(r_buff[3]) == self.addr and (not visited):
            #print("check_message checkpoint 2")
            if self.calc_new_message(r_buff[5], path):
                #print("check_message checkpoint 3")

                #print(sender)
                id = int(sender[1], 16) + int(sender[2], 16)
                #we store this data so we can check for duplicates. r_buff[5] here is the time sent from the node requesting data
                self.received_time = (r_buff[5], id)
                #####We set path to r_buff[4], so we can get the array of nodes we to send the information back through. 
                ##### we need the path to navigate the way back to original sender of request.


                #####This block makes sure that if we have seen the original sender of the request before, we also ignore the message
                if  self.store_received_requests == int(path[0]):
                    #print("check_message checkpoint 3.1")
                    print("We have seen a message with this origin before, passing")
                    pass
                else:
                    #print("check_message checkpoint 3.2")
                    self.path = path
                    #print(path)
                    #print(path[0])
                    self.store_received_requests = int(path[0])

            #print("check_message checkpoint 4")
        elif int(r_buff[3]) != self.addr and (not visited):
            #print("check_message checkpoint 5")
            if self.calc_new_message(r_buff[5], path):
                #print("check_message checkpoint 6")
                ###if we have the node in reachable_dev, only send message to it instead of broadcast!!!!
                id = int(sender[1], 16) + int(sender[2], 16)

                self.received_time = (r_buff[5], id)
                #print("check_message checkpoint 7")
                #####appending addr to path 
                path = path + str(self.addr)
                r_buff[4] = path
                #print("check_message checkpoint 8")
                self.forward = r_buff[2:-1]

                if  self.store_received_requests == int(path[0]):
                    #print("check_message checkpoint 8.1")
                    print("We have seen a message with this origin before, passing")
                    pass
                else:
                    #print("check_message checkpoint 8.2")
                    self.store_received_requests = int(path[0])
            else: 
                pass
        else: 
            pass
        #print("check_message checkpoint 9")

    def ret_data(self, r_buff, log_toa):
        #print("Check ret_data 1, we're inside")
        #print(r_buff)
        path = r_buff[3]
        #print(path)
        #print(len(path))
        ####payload is the cpu temperature
        payload = r_buff[4]
        ####if path is empty, we're the final node.
        if len(path) > 0:
            #print("check ret_data 2, we're still alive")
            self.data = (payload, path, r_buff[5])
            #print(type(self.data[0]))
            #print("set data")

        else:
            ###enter here if we're the start node (returning data enters here.)
            print("We received the requested data from Node: " +str(self.end_node) + ", the message is: " + str(payload))
            clock = datetime.datetime.now()
            c_time = float(clock.minute * 60) + float(clock.second) + (clock.microsecond / 1000000)
            o_time = float(payload)
            TOA = c_time - o_time
            print(payload)
            print(TOA)
            log_toa.info("Time on air: " +str(TOA))
            ####r_buff[5] is the backup path. 
            self.ack_info = (r_buff[5], self.end_node)
            #print(self.ack_info)
            #print(self.end_node)
            self.end_node = ""
            self.send_ack = True

    def compare_time(self):
        #####TODO: Test if this function works at beginning of hours!! should work with the new timeout varaible
        #print("compare time check 1")
        ####TODO: maybe fix this shit so we dont have to make the object as a string and then convert it to a datetime object.
        datetimer = datetime.datetime.now().strftime("%d-%m-%y %H:%M:%S")
        clock = datetime.datetime.strptime(datetimer, '%d-%m-%y %H:%M:%S')
        #print("compare time check 2")
        current_m = int(clock.strftime("%M")) * 60
        current_s = int(clock.strftime("%S"))
        current_time = current_m + current_s
        timeout = 60*3.5
        #print("compare time check 3")
        for i in self.reachable_dev:
            #print(i[1])
            timer = int(i[1])
            #print("We made it inside the for loop in compare time 2")
            #print(type(timer))
            #print(type(timeout))
            #print(current_time)
    
            
            if (timer + int(timeout)) < int(current_time):
                #print("We made it inside the for loop in compare time 3")
                self.reachable_dev.remove(i)
                print("We removed: "+ str(i) + " due to expiration exceeded")

            ####If the timer has moved to a new hour, we check if the value is negative, if it is, we add 3600 to the timer and check with that timer.
            elif (int(timer + int(timeout))) - current_time < -(timeout+10):
                #print("we wint inside logical if")
                logical_time = current_time + 3600
                if ((timer + int(timeout)) < logical_time):
                    del self.reachable_dev[i]
                    print("We removed: "+str(i[0]) + " due to expiration exceeded")
            else:
                pass

    #####Added functionality for receiving node_id as we expect self.ser.inWaiting() to have 1 extra entry in its list.
    def receive(self, log_receive, log_error, log_toa):
        if self.ser.inWaiting() > 0:
            #print("receive checkpoint 1")
            #####Sleep has to be appropriate. If too small, it will not read the entire message!!
            time.sleep(0.3)
            self.receive_icr += 1
            log_receive.info("Number of received messages %d", self.receive_icr)
            r_buff = self.ser.read(self.ser.inWaiting())
            #print("receive checkpoint 2")
            rec = str(r_buff)
            r_buff_in_string = rec.split(",")

    
            #print("receive checkpoint 3")
            #####Made a check to see if the message was for us
            #r_buff[0] == receiving node address, r_buff[1] == sender node address, r_buff[2] == frequency, r_buff[3] == node_id of receiver, r_buff[4] == sender node_id, r_buff[5] == ack_id, r_buff[6]+ == payload
            ##### TODO: Make the else statement reroute the message to the right owner if in routing table or send to next hop closer to the right owner if not directly connected.
            ###This ugly ass else/if statement is only here because switch statements are only available for python3.10 and newer.
            try:
                print(int(chr(r_buff[5])))
                if int(chr(r_buff[5])) == 0:
                    pass

            except:
                self.error_icr += 1
                log_error.info("Number of error messages %d", self.error_icr)
                print("Unknown message type")
            else:
                if int(chr(r_buff[5])) == 0:
                    #print("heartbeat check 1")
                    #print(r_buff_in_string)
                    timer = r_buff_in_string[3]
                    dateT = datetime.datetime.strptime(timer, '%d-%m-%y %H:%M:%S')
                    m = int(dateT.strftime("%M")) * 60
                    s = int(dateT.strftime("%S"))
                    total_seconds = m + s
                    #print("heartbeat check 2")
                    self.reachable_dev.append((int((r_buff[1]<<8) + r_buff[2]), total_seconds))


                    #self.reachable_dev[1] = self.reachable_dev[1] + str()
                    #self.reachable_dev[0] = self.reachable_dev[0] + str((r_buff[1]<<8) + r_buff[2])
                    
                    print("Neighbour table: " + str(self.reachable_dev))
                elif int(chr(r_buff[5])) == 1:
                    #print("Receive checkpoint 4")
                    self.check_message(r_buff_in_string)
                    
                    #print("Noted ack_id")
                elif int(chr(r_buff[5])) == 2:
                    #print("checkpoint: ack_id = 2, we're returning data")
                    self.ret_data(r_buff_in_string, log_toa)
                elif int(chr(r_buff[5])) == 3:
                    ####If we're in here the message sent has path in 3rd slot
                    #print("Ack test receive")
                    #print(r_buff_in_string[3])
                    #print(r_buff_in_string[-1])
                    if r_buff_in_string[3] == r_buff_in_string[-1]:
                        #####This value is used in forward ack function when calling assigning info
                        self.got_ack = True
                        print("Acknowledgement has been received successfully")
                    else:
                        #####get path from r_buff_in_string and pass to forward ack function in main file
                        #print(r_buff_in_string)
                        self.ack_info = (r_buff_in_string[3], r_buff_in_string[4])
                        self.forward_ack = True
                        print("Forwarding acknowledgement message")

                else:
                    #error handling if ack_id invalid value
                    self.error_icr += 1
                    log_error.info("Number of error messages %d", self.error_icr)
                    print("Unknown message type")
                
                
            # print the rssi
            if self.rssi:
                # print('\x1b[3A',end='\r')
                print("the packet rssi value: -{0}dBm".format(256-r_buff[-1:][0]))
                self.get_channel_rssi()
            else:
                self.ser.flushInput()
                pass
                #print('\x1b[2A',end='\r')

    def get_channel_rssi(self):
        GPIO.output(self.M1,GPIO.LOW)
        GPIO.output(self.M0,GPIO.LOW)
        time.sleep(0.1)
        self.ser.flushInput()
        self.ser.write(bytes([0xC0,0xC1,0xC2,0xC3,0x00,0x02]))
        time.sleep(0.1)
        re_temp = bytes(5)
        if self.ser.inWaiting() > 0:
            time.sleep(0.1)
            re_temp = self.ser.read(self.ser.inWaiting())
        if re_temp[0] == 0xC1 and re_temp[1] == 0x00 and re_temp[2] == 0x02:
            print("the current noise rssi value: -{0}dBm".format(256-re_temp[3]))
            # print("the last receive packet rssi value: -{0}dBm".format(256-re_temp[4]))
        else:
            # pass
            print("receive rssi value fail")
            # print("receive rssi value fail: ",re_temp)
