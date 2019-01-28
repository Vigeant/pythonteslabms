#!/usr/bin/env python3

"""
Tesla BMS script V0.2. Written by Jarrod Tuma.
This script opens up an FTDI uart at 612500bps, then sends some commands to the
Tesla BMS to configure it for the first time.
It will print the replies in hex format, and check the CRC
Finally the readADCs function will print out the ADC results as voltages 
and turn on one of the balancing resistors to test
"""
#serPort="COM3" # on windows
#serPort="/dev/ttyAMA0" # on RPI 3b+
serPort="/dev/ttyUSB1" # on RPI 3b+
#Import modules
import serial
import time
import crcmod #run "pip install crcmod" to install this

def main():
    #Reset all connected modules with a broadcast
    print('sending reset broadcast')
    sendData(Write,[BROADCAST,RESET,0xA5])
    #set address
    print('setting address 1')
    address=0x01
    sendData( Write, [0x00, ADDRESS_CONTROL, address|0x80]) #set the address
    #configure ADC
    sendData( Write, [address, ADC_CONTROL, 0x3D])
    #configure IO
    sendData( Write, [address, IO_CONRTOL, 0x03])
    #clear faults
    sendData( Write, [address, ALERT_STATUS, 0x80])
    sendData( Write, [address, ALERT_STATUS, 0x00])
    sendData( Write, [address, FAULT_STATUS, 0x08])
    sendData( Write, [address, FAULT_STATUS, 0x00])
    readADCs( address)
    #set balance timeout to 2s
    sendData(Write,[address,CB_TIME,0x02])
    #turn on balancing FET for cell 0
    sendData(Write,[address,CB_CTRL,0x01])
    #read out the voltage again
    readADCs( address)

# ~~ All the helper functions follow ~~ #

def tx(write,data):
    crc=0
    data[0]=data[0]<<1 #shift address for first byte as format is 0bBAAAAAAW, where B=blocking bit, A=address, W=write bit
    if(write): #use CRC if writing
        data[0]=data[0] | 0x01 #set write bit
        crc=crc8f(bytearray(data))
        data.append(crc)
    print('transmitting...')
    print('%r'% data)
    ser.write(bytearray(data))
    print('transmitted...')
    return crc
    
def sendData(write,data):
    #this fn just writes data and prints the reply
    crc=tx(write,data)
    time.sleep(0.1)
    rxData=[]
    print('RX: ',end='')
    print('\n')
    while(ser.inWaiting()):
        rxData.append(ord(ser.read()))
    #print(rxData) #print in dec
    print([hex(b) for b in rxData]) #print in hex
    
    #Check CRC
    if write == False: #for Reads we need to calculate a CRC to compare
        crc=crc8f(bytearray(rxData[0:len(rxData)-1]))
    rxCRC=rxData[len(rxData)-1] #last bit in reply is CRC
    if(rxCRC != crc):
        print("CRC FAIL")
        return False
    else:        
#        print("CRC PASS")
        return rxData
        
def readAll(address):
    ser.write(bytearray([address<<1, 0, 0x4C]))#read out EEPROM
    time.sleep(0.1)
    i=0
    while(ser.inWaiting()):
        if i==0:
            for x in range(3):
                print(ser.read().hex())   
        if ( ((i>=0x13) & (i<=0x1F)) | ((i>=0x26) & (i<=0x2F)) | ((i>=0x35) & (i<=0x39)) | (i==0x3E) ):
            print('r', end=' ')
            ser.read()
        else:     
            print()
            print(hex(i), end=': ')
            print(ser.read().hex(), end='')
        i=i+1
    print('')

def readADCs(address):
    sendData(Write,[address,0x34,1])
    rxData=sendData(Read,[address,0x01,0x11]) #read out all ADC results
    if(rxData):
        #covert as per datasheet
        print(round((rxData[3]*256 + rxData[4]) * 33.333 / 16383, 3))#VBAT
        for n in [5,7,9,11,13,15]:
            print(round((rxData[n]*256 + rxData[n+1]) * 6.250 / 16383, 3))#Vcell


#setup CRC
crc8f=crcmod.mkCrcFun(0x107,initCrc=0,rev=False)
#Define constants
Write=True
Read=False
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
#open serial port
try:
    ser = serial.Serial( # set parameters
        port=serPort,
        baudrate=612500,
        timeout=1
    )
    ser.isOpen() # try to open port
    print ("port has been opened")

except IOError: # if port is already opened, close it and open it again
    try:
        ser.close()
        ser.open()
        print ("port was already open, was closed and opened again")
    except: #ser object doesn't even exist? must be a port setting fault
        ser=False    
        print ("Check port settings!")

#Run main code
if ser:
    main()
    
"""
#read ADCs
sendData(Write,[address, regADC_CONTROL, 0b00111101]) #set channels to read
sendData(Write,[address, regADC_CONVERT, 0x01]) #start conversion
sendData(Read,[address,0x01,0x11]) #read out all ADC results
"""



