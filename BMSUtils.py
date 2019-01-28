#!/usr/bin/env python3

"""
Tesla BMS utilities to talk to the module

based on the initial work from bellow

Tesla BMS script V0.2. Written by Jarrod Tuma.
This script opens up an FTDI uart at 612500bps, then sends some commands to the
Tesla BMS to configure it for the first time.
It will print the replies in hex format, and check the CRC
Finally the readADCs function will print out the ADC results as voltages
and turn on one of the balancing resistors to test
"""

#Import modules
import serial
import time
import logging
#import crcmod #run "pip install crcmod" to install this

#constants
REG_DEV_STATUS     = 0
REG_GPAI           = 1
REG_VCELL1         = 3
REG_VCELL2         = 5
REG_VCELL3         = 7
REG_VCELL4         = 9
REG_VCELL5         = 0xB
REG_VCELL6         = 0xD
REG_TEMPERATURE1   = 0xF
REG_TEMPERATURE2   = 0x11
REG_ALERT_STATUS   = 0x20
REG_FAULT_STATUS   = 0x21
REG_COV_FAULT      = 0x22
REG_CUV_FAULT      = 0x23
REG_ADC_CTRL       = 0x30
REG_IO_CTRL        = 0x31
REG_BAL_CTRL       = 0x32
REG_BAL_TIME       = 0x33
REG_ADC_CONV       = 0x34
REG_ADDR_CTRL      = 0x3B
REG_RESET          = 0x3C

MAX_MODULE_ADDR    = 0x3E
BROADCAST = 0x3F

def printh(data):
    print([hex(b) for b in data])

def u16(data):
    return ((data[0] << 8) + data[1])

class Comms:
    class __Comms:
        def __init__(self, serPort):
            #self.serPort = serPort
            #open serial port
            try:
                self.ser = serial.Serial( # set parameters
                    port=serPort,
                    baudrate=612500,
                    timeout=1
                )
                self.ser.isOpen() # try to open port
                logging.debug("port has been opened")

            except IOError: # if port is already opened, close it and open it again
                try:
                    self.ser.close()
                    self.ser.open()
                    logging.debug("port was already open, was closed and opened again")
                except: #ser object doesn't even exist? must be a port setting fault
                    self.ser=False
                    logging.debug("Check port settings!")
                    Quit()

        def __str__(self):
            return repr(self) + self.serPort

        def __genCRC(self, data):
            generator = 0x07
            crc = 0

            for c in data:
                crc ^= c

                for i in range(8):
                    if (crc & 0x80) != 0:
                        crc = ((crc << 1) ^ generator) & 0xff
                    else:
                        crc = (crc << 1) & 0xff

            return crc

        def __tx(self, write,data):
            crc=0
            data[0]=data[0]<<1 #shift address for first byte as format is 0bBAAAAAAW, where B=blocking bit, A=address, W=write bit
            if(write): #use CRC if writing
                data[0]=data[0] | 0x01 #set write bit
                crc=self.__genCRC(bytearray(data))
                data.append(crc)
            #print('transmitting...')
            #print([hex(b) for b in data])
            self.ser.write(bytearray(data))
            #print('transmitted...')
            return crc

        def __sendData(self, write,data):
            #this fn just writes data and prints the reply
            crc=self.__tx(write,data)
            time.sleep(0.1)
            rxData=[]
            #print('RX: ',end='')
            #print('\n')
            while(self.ser.inWaiting()):
                rxData.append(ord(self.ser.read()))
            #print(rxData) #print in dec
            #print([hex(b) for b in rxData]) #print in hex

            #Check CRC
            if write == False: #for Reads we need to calculate a CRC to compare
                crc=self.__genCRC(bytearray(rxData[0:len(rxData)-1]))
                #print([hex(b) for b in bytearray(rxData[0:len(rxData)-1])])
            rxCRC=rxData[len(rxData)-1] #last bit in reply is CRC
            if(rxCRC != crc):
                logging.debug("CRC FAIL 0x%x, 0x%x" % (rxCRC, crc))
                return False
            else:
        #        print("CRC PASS")
                return rxData

        def __sendDataNoCRC(self, write,data):
            #this fn just writes data and prints the reply
            crc=self.__tx(write,data)
            time.sleep(0.1)
            rxData=[]
            #print('RX: ',end='')
            #print('\n')
            while(self.ser.inWaiting()):
                rxData.append(ord(self.ser.read()))
            #print(rxData) #print in dec
            #print([hex(b) for b in rxData]) #print in hex
            return rxData


        def read(self, moduleAddress, address, numBytes):
            return self.__sendData(False, [moduleAddress, address, numBytes])

        def readNoCRC(self, moduleAddress, address, numBytes):
            return self.__sendDataNoCRC(False, [moduleAddress, address, numBytes])

        def write(self, moduleAddress, address, data):
            return self.__sendData(True, [moduleAddress, address, data])



        def test(self):

            BROADCAST = 0x3F
            ADDRESS_CONTROL=0x3b
            ADC_CONTROL = 0x30
            ADC_CONVERT = 0x34
            IO_CONRTOL = 0x31
            ALERT_STATUS = 0x20
            FAULT_STATUS = 0x21
            CB_TIME = 0x33
            CB_CTRL = 0x32
            RESET = 0x3C

            #Reset all connected modules with a broadcast
            logging.debug('sending reset broadcast')
            self.write(BROADCAST, RESET, 0xA5)
            #sendData(Write,[BROADCAST,RESET,0xA5])

            #set address
            logging.debug('setting address 1')
            address=0x01
            self.write(0, ADDRESS_CONTROL, address|0x80)
            #sendData( Write, [0x00, ADDRESS_CONTROL, address|0x80]) #set the address

            #configure ADC
            self.write(address, ADC_CONTROL, 0x3D)
            #sendData( Write, [address, ADC_CONTROL, 0x3D])

            #configure IO
            self.write(address, IO_CONRTOL, 0x03)
            #sendData( Write, [address, IO_CONRTOL, 0x03])

            #clear faults

            self.write(address, ALERT_STATUS, 0x80)
            self.write(address, ALERT_STATUS, 0x00)
            self.write(address, FAULT_STATUS, 0x08)
            self.write(address, FAULT_STATUS, 0x00)


            self.readADCs(address)

            #set balance timeout to 2s
            self.write(address,CB_TIME,0x02)
            #turn on balancing FET for cell 0
            self.write(address,CB_CTRL,0x01)
            #read out the voltage again
            time.sleep(2)
            self.readADCs(address)


        def readADCs(self, address):
            self.write(address,0x34,1)
            rxData = self.read(address,0x01,0x11) #read out all ADC results
            if(rxData):
                #covert as per datasheet
                print(round((rxData[3]*256 + rxData[4]) * 33.333 / 16383, 3))#VBAT
                for n in [5,7,9,11,13,15]:
                    print(round((rxData[n]*256 + rxData[n+1]) * 6.250 / 16383, 3))#Vcell

    instance = None

    def __init__(self, serPort = "/dev/ttyUSB1"):
        if not Comms.instance:
            Comms.instance = Comms.__Comms(serPort)

    def __getattr__(self, name):
        return getattr(self.instance, name)
#Run main code
#a = Comms("/dev/ttyUSB1")
#a.test()
