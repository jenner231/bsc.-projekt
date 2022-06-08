# Long Range radio network in a mesh topology.

# Description
Note: This is a bachelor project created at Aarhus university by Magnus Tang and Jens Fisker.

The project uses the LoRa PHY technology to transmit messages in a mobile ad hoc network. The idea behind is to find an alternative to the already established LoRaWAN standard, which is deployed in a star topology using centralized base stations called gateways. This project aims to decentralize communication, and establish a long range, low cost, low batteri consumption mesh network solution to the LoRa PHY technology. This will allow for more use in more unurbanized areas, where internet else in inaccessible. 

Note however that this is only a prototype.

# How to install and run the project
Hardware requirements to run the project:
2 Raspberry PI´s with the debian 32bit raspberry OS and python 3 installed. 2 Waveshare LoRa SX1262 868M LoRa HATs and 2 868 MHz antennas (for europe only - for use in other regions please do research on your regional LoRa frequency, general frequncies can be found at https://www.thethingsnetwork.org/docs/lorawan/regional-parameters/.

Each of the PI´s should be configured to enable serial-port. To do so open a terminal and run the command:

$ sudo raspi-config

In the raspi-config navigate to the Interface option tab, select serial and configure your pi as shown in the images below:

![image](https://user-images.githubusercontent.com/61544552/172643158-63b5d184-9c0a-4bab-a83d-aac9cf38da8e.png)

The LoRa modules should now be configured with jumpers and attached to the raspberry PI as shown below:

![image](https://user-images.githubusercontent.com/61544552/172643904-0e1c8fbb-17f1-4468-a31a-3cf10872a2d5.png)

For additional information, please refer this website:
https://www.waveshare.com/wiki/SX1262_868M_LoRa_HAT

Now clone this repository onto the PIs and open a terminal. Navigate to the folder to which you have cloned the repository and run the commands:

$ cd bsc.-projekt
$ cd python
$ sudo python3 main_test.py


![image](https://user-images.githubusercontent.com/61544552/172646089-53e94d3e-2012-4ed2-85e1-10c7eeffbc81.png)


# How to use the project
