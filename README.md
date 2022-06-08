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

In the config

![image](https://user-images.githubusercontent.com/61544552/172643158-63b5d184-9c0a-4bab-a83d-aac9cf38da8e.png)

 
 



# How to use the project
