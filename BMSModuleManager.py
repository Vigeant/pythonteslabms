#!/usr/bin/env python3

from BMSUtils import *
from BMSModule import BMSModule
import time
import logging

logging.basicConfig(level=logging.DEBUG)

class BMSModuleManager:

    packVolt = 0.0              # All modules added together
    Pstring = 0
    LowCellVolt = 0.0
    HighCellVolt = 0.0
    lowestPackVolt = 0.0
    highestPackVolt = 0.0
    lowestPackTemp = 0.0
    highestPackTemp = 0.0
    modules = []               # store data for as many modules as we've configured for.
    batteryID = 0
    #numFoundModules = 0        # The number of modules that seem to exist
    isFaulted = False
    spack = 0

    def __init__(self):
        self.comms = Comms('/dev/ttyUSB1')

        #reset all modules and assign adresses
        self.autoAssignModuleAddresses()

        #clear all faults
        self.clearFaults()

        #control loop
            # Read values from boards
        self.readAllVoltTemp()
            # write db with latest values
            # read db for orders from website
            # Perform orders (auto load balancing, clear faults ...)
            # sleep 2 minute and redo.
        self.balanceCells(7)

    def balanceCells(self, duration=5):
        #1 build array with all cell voltages
        allCellsV = []
        tolerance = 0.05 #anything within this V is good
        for i in range(len(self.modules)):
            module = self.modules[i]
            allCellsV += module.cellVolt
        minCellV = min(allCellsV)

        cellBalance = 0
        for i in range(len(allCellsV)):
            if allCellsV[i] > (minCellV + tolerance):
                #compute module and cell
                modIndex = i // 6
                cellNum = i % 6
                modAddr = modIndex + 1
                cellBalance |= 1 << cellNum

            #if balancing is required and if at last cell of module
            if (cellBalance > 0) & (cellNum == (6 - 1) ):
                logging.debug('[!] Setting balancing duration on Module: %d : 0x%X' % (modAddr,cellBalance))
                self.comms.write(modAddr, REG_BAL_TIME, duration)
                time.sleep(0.02)
                self.comms.write(modAddr, REG_BAL_CTRL, cellBalance)
                cellBalance = 0

        for i in range(10):
            logging.debug(self.comms.read(modAddr, REG_BAL_CTRL, 1))
            time.sleep(1)




    def readAllVoltTemp(self):
        self.packVolt = 0.0
        self.stopBalancing()
        time.sleep(0.02)

        for module in self.modules:
            logging.debug('[!] Module %i || Reading voltage and temperature values' % module.moduleAddress)
            module.readVoltTemp()
            logging.debug('[!] Module voltage: %f' % module.moduleVolt)
            logging.debug('[!] (since reset) Lowest Cell V: %f\tHighest Cell V: %f' % (min([a for a in module.lowestCellVolt]), max([a for a in module.highestCellVolt])))
            logging.debug('[!] (current) Cell V: ' + str(['%f ' % a for a in module.cellVolt]))
            logging.debug('[!] Temp1: %f\t\tTemp2: %f' % (module.temperatures[0], module.temperatures[1]))
            self.packVolt += module.moduleVolt
            self.lowestPackTemp = min(self.lowestPackTemp, module.lowestTemperature)
            self.highestPackTemp = max(self.highestPackTemp, module.highestTemperature)

    def stopBalancing(self):
        self.comms.write(BROADCAST, REG_BAL_CTRL, 0x00)

    def sleepBoards(self):
        logging.debug('[!] Putting the board to bed')
        self.comms.write(BROADCAST, REG_IO_CTL, 0x04)
        logging.debug('[+] Boards are sound asleep!')

    def wakeBoards(self):
        logging.debug('[!] Waking up the boards')
        self.comms.write(BROADCAST, REG_IO_CTL, 0x00) #clear sleep bit
        self.comms.write(BROADCAST, REG_ALERT_STATUS, 0x04) #cause a reset
        self.comms.write(BROADCAST, REG_ALERT_STATUS, 0x00) #clear alert
        logging.debug('[+] Boards are awake!')

    def clearFaults(self):
        logging.debug('[!] Resetting Alerts and faults')
        self.comms.write(BROADCAST, REG_ALERT_STATUS, 0xff)
        self.comms.write(BROADCAST, REG_ALERT_STATUS, 0)
        self.comms.write(BROADCAST, REG_FAULT_STATUS, 0xff)
        self.comms.write(BROADCAST, REG_FAULT_STATUS, 0)
        self.isFaulted = False
        logging.debug('[+] Sucessfully reset Alerts and faults')

    def resetModuleAddresses(self):
        logging.debug('[!] Resetting module addresses')
        val = None
        while val != [0x7f, 0x3c, 0xa5, 0x57]:
            val = self.comms.write(BROADCAST, REG_RESET, 0xA5)
            time.sleep(0.02)
        logging.debug('[+] Sucessfully reset module addresses')

    def autoAssignModuleAddresses(self):
        self.modules = []
        self.resetModuleAddresses()
        logging.debug('[!] Assigning module addresses')
        for i in range(63):
            val = self.comms.readNoCRC(0, 0, 1)
            if val[:3] == [0x80, 0, 1]:
                logging.debug("[!] Board 00 found!")
                self.modules.append(BMSModule(self.comms))
                self.modules[i].moduleAddress = i+1
                val2 = [0,0,0]
                logging.debug("[!] Setting its address to %d" % self.modules[i].moduleAddress)
                while val2[:3] != [0x81, REG_ADDR_CTRL, self.modules[i].moduleAddress | 0x80]:
                    val2 = self.comms.write(0, REG_ADDR_CTRL, self.modules[i].moduleAddress | 0x80)
                    time.sleep(0.02)
            else:
                break
        logging.debug('[+] Sucessfully assigned module addresses')


bmsmm = BMSModuleManager()
