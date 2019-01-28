#!/usr/bin/env python3

from BMSUtils import *
import logging
import math

class BMSModule:

    #properties
    cellVolt = [None] * 6
    lowestCellVolt = [200.0] * 6
    highestCellVolt = [0.0] * 6
    moduleVolt = 0
    temperatures = [None] * 2
    lowestTemperature = 200.0
    highestTemperature = -100.0
    lowestModuleVolt = 200.0
    highestModuleVolt = 0.0
    IgnoreCell = 0
    exists = 0
    alerts = 0
    faults = 0
    COVFaults = 0
    CUVFaults = 0
    sensor = 0
    moduleAddress = 0
    scells = 0

    def readStatus(self):
        buf = self.comms.read(self.moduleAddress, REG_ALERT_STATUS, 0x04)
        (self.alerts, self.faults, self.COVFaults, self.CUVFaults) = buf[3:7]

    def readVoltTemp(self):
        self.readStatus()
        logging.debug("Module %i   alerts=%X   faults=%X   COV=%X   CUV=%X" % (self.moduleAddress, self.alerts, self.faults, self.COVFaults, self.CUVFaults))
        #ADC Auto mode, read every ADC input we can (Both Temps, Pack, 6 cells)
        self.comms.write(self.moduleAddress, REG_ADC_CTRL, 0x3d)
        #enable temperature measurement VSS pins
        self.comms.write(self.moduleAddress, REG_IO_CTRL, 0x03)
        #start all ADC conversions
        self.comms.write(self.moduleAddress, REG_ADC_CONV, 0x01)
        #start reading registers at the module voltage registers
        #read 18 bytes (Each value takes 2 - ModuleV, CellV1-6, Temp1, Temp2)
        buf = self.comms.read(self.moduleAddress, REG_GPAI, 0x12)
        retModuleVolt = float(u16(buf[3:5])) * 0.0020346293922562
        self.highestModuleVolt = max(self.highestModuleVolt, retModuleVolt)
        self.lowestModuleVolt = min(self.lowestModuleVolt, retModuleVolt)
        self.moduleVolt = 0.0
        for i in range(len(self.cellVolt)):
            self.cellVolt[i] = float(u16(buf[5+(i*2) : 7+(i*2)])) * 0.000381493
            self.highestCellVolt[i] = max(self.highestCellVolt[i],  self.cellVolt[i])
            self.lowestCellVolt[i] = min(self.lowestCellVolt[i], self.cellVolt[i])
            self.moduleVolt += self.cellVolt[i]

        tempTemp = (1.78 / ((float(u16(buf[17:19])) + 2) / 33046.0) - 3.57)
        tempTemp *= 1000.0
        tempCalc =  1.0 / (0.0007610373573 + (0.0002728524832 * math.log(tempTemp)) + (math.pow(math.log(tempTemp), 3) * 0.0000001022822735))
        self.temperatures[0] = tempCalc - 273.15

        tempTemp = (1.78 / ((float(u16(buf[19:21])) + 9) / 33068.0) - 3.57)
        tempTemp *= 1000.0
        tempCalc =  1.0 / (0.0007610373573 + (0.0002728524832 * math.log(tempTemp)) + (math.pow(math.log(tempTemp), 3) * 0.0000001022822735))
        self.temperatures[1] = tempCalc - 273.15

        self.lowestTemperature = min(self.lowestTemperature, self.temperatures[0], self.temperatures[1])
        self.highestTemperature = max(self.highestTemperature, self.temperatures[0], self.temperatures[1])

        logging.debug("Got voltage and temperature readings")

    def __init__(self, serialConnection):
        self.comms = serialConnection
        #self.comms.test()
        self.clearModule()

    def clearModule(self):
        self.cellVolt = [None] * 6
        self.lowestCellVolt = [200.0] * 6
        self.highestCellVolt = [0.0] * 6
        self.moduleVolt = 0
        self.temperatures = [None] * 2
        self.lowestTemperature = 200.0
        self.highestTemperature = -100.0
        self.lowestModuleVolt = 200.0
        self.highestModuleVolt = 0.0
        self.IgnoreCell = 0
        self.exists = 0
        self.alerts = 0
        self.faults = 0
        self.COVFaults = 0
        self.CUVFaults = 0
        self.sensor = 0
        self.moduleAddress = 0
        self.scells = 0

    def stopBalancing(self):
        self.comms.write(moduleAddress, REG_BAL_CTRL, 0x00)


#module1 = BMSModule(Comms('/dev/ttyUSB1'))
