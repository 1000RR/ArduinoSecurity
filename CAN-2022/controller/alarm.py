import serial
from datetime import datetime 
import math
import numpy as np
import time
import atexit
import json
import subprocess
import os
from threading import Thread


debug = False
LISTEN_PORT=8080
memberDevices = {} #map of {string hex id:{properties}}
denonId = 0x77
testAlarmId = 0xDE
checkPhonesId = 0x17
garageDoorOpenerId = 0xD0
garageDoorSensorId = 0x30
exceptMissingDevices = {hex(denonId): True, hex(garageDoorOpenerId): True}
denonPlayThread = 0
lastSentMessageTimeMsec = 0
homeBaseId = 0x14 #interdependent with deviceDictionary
broadcastId = 0x00
pastEvents = []
alarmed = False
alarmedDevicesInCurrentArmCycle = {}
missingDevicesInCurrentArmCycle = {}
everTriggeredWithinAlarmCycle = {} #map of {string hex id:int alarmTimeSec}
currentlyAlarmedDevices = {} #map of {string hex id:int alarmTimeSec}
currentlyMissingDevices = []
everMissingDevices = {}
lastAlarmTime = 0
armed = False #initial condition
lastArmedTogglePressed = 0
deviceAbsenceThresholdSec = 7
firstPowerCommandNeedsToBeSent = True
timeAllottedToBuildOutMembersSec = 2
initWaitSeconds = 5
alarmReason = ""
sendTimeoutMsec = 500
lastCheckedMissingDevicesMsec = 0
checkForMissingDevicesEveryMsec = 750
currentAlarmProfile = 0 # 0 = default
threadShouldTerminate = False
canDebugMessage = ""
shouldSendDebugRepeatedly = False
shouldSendDebugMessage = False
alwaysKeepOnSet = {"0x30", "0x31"} #set of devices to always keep powered on (active). This should be limited to non-emitting sensors.
avrSoundChannel = "SAT/CBL"


deviceDictionary = {
    "0x80": "SENSOR | GARAGE MOVEMENT | 0x80",
    "0x75": "SENSOR | KITCHEN MOVEMENT | 0x75",
    hex(garageDoorSensorId): "SENSOR | GARAGE CAR DOOR | " + hex(garageDoorSensorId),
    "0x31": "SENSOR | GARAGE SIDE DOOR | 0x31",
    "0x40": "SENSOR | KITCHEN BACK DOOR | 0x40",
    "0x50": "SENSOR | FRONT DOOR | 0x50",
    hex(homeBaseId): "HOMEBASE | HOME BASE | 0x14",
    "0xFF": "HOMEBASE | HOME BASE communicating to its arduino | 0xFF",
    "0x10": "ALARM | LAUNDRY FIRE ALARM BELL | 0x10",
    "0x15": "ALARM | GARAGE PIEZO LOUD ALARM | 0x15",
    "0x99": "ALARM | OFFICE ALARM | 0x99",
    hex(denonId): "ALARM | OFFICE SPEAKERS | " + hex(denonId),
    hex(checkPhonesId): "SENSOR | VIRTUAL sensor for getting attention | " + hex(checkPhonesId),
    hex(testAlarmId): "SENSOR | VIRTUAL sensor for triggering a test alarm | " + hex(testAlarmId),
    hex(garageDoorOpenerId): "OPENER | GARAGE DOOR OPENER | " + hex(garageDoorOpenerId)
}


mp3AlarmDictionary = {
    "0x80": "garagemovement.mp3",
    "0x75": "kitchenmovement.mp3",
    hex(garageDoorSensorId): "garagedoor.mp3",
    "0x31": "garagesidedoor.mp3",
    hex(checkPhonesId): "checkyourphones.mp3",
    "0x50": "frontdoor.mp3",
    "0x40": "kitchenbackdoor.mp3"
}


alarmProfiles = [
{
    "index": 0,
    "name": "Night",
    "sensorsThatTriggerAlarm": [ "0x31", "0x30", "0x40", "0x50"],
    "missingDevicesThatTriggerAlarm": ["0x31", "0x30", "0x40", "0x50"],
    "alarmOutputDevices": ["0x99", hex(denonId), "0x15", "0x10"],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 1,
    "name": "Away",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "alarmOutputDevices": ["0x99", "0x15", "0x10", hex(denonId)],
    "playSound": "scaryalarm.mp3",
    "playSoundVolume": 45,
    "alarmTimeLengthSec": 30 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 2,
    "name": "Visual Test - Perimeter",
    "sensorsThatTriggerAlarm": ["0x31", "0x30", "0x50", "0x40"],
    "missingDevicesThatTriggerAlarm": ["0x31", "0x30", "0x40", "0x50"],
    "alarmOutputDevices": ["0x51"],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 3,
    "name": "Office - Perimeter",
    "sensorsThatTriggerAlarm": ["0x31", "0x30", "0x50", "0x40"],
    "missingDevicesThatTriggerAlarm": ["0x31", "0x30", "0x50", "0x40"],
    "alarmOutputDevices": ["0x99"],
    "alarmTimeLengthSec": 5 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 4,
    "name": "Night - All Alarms 10s | Garage Perimeter Sensors",
    "sensorsThatTriggerAlarm": [ "0x31", "0x30"],
    "missingDevicesThatTriggerAlarm": ["0x31", "0x30"],
    "alarmOutputDevices": ["0x99", hex(denonId), "0x15", "0x10"],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 5,
    "name": "Night - All Alarms 10s | All Sensors",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "alarmOutputDevices": ["0x99", hex(denonId), "0x15", "0x10"],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 6,
    "name": "All Alarms 5s | All Sensors", #all missing and all triggers BROADCAST ALARM
    "alarmTimeLengthSec": 5 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 7,
    "name": "Visual Test - All Sensors",
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "alarmOutputDevices": ["0x51"],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 8,
    "name": "Visual Alarm 10s | Garage Sensors",
    "sensorsThatTriggerAlarm": ["0x31", "0x30", "0x80"],
    "missingDevicesThatTriggerAlarm": ["0x31", "0x30", "0x80"],
    "alarmOutputDevices": ["0x51"],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 9,
    "name": "Test - Denon Alarm 10s | All Sensors",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "alarmOutputDevices": [hex(denonId)],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 10,
    "name": "Night - Office Alarms 10s | Garage side door & movement",
    "sensorsThatTriggerAlarm": [ "0x31", "0x80"],
    "missingDevicesThatTriggerAlarm": ["0x31", "0x80"],
    "alarmOutputDevices": ["0x99", hex(denonId)],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 11,
    "name": "Night - Office Alarms 10s | Garage side door & movement; Kitchen movement",
    "sensorsThatTriggerAlarm": [ "0x31", "0x80", "0x75"],
    "missingDevicesThatTriggerAlarm": ["0x31", "0x80", "0x75"],
    "alarmOutputDevices": ["0x99", hex(denonId)],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 12,
    "name": "Night - Office Buzzer 7s | Garage side door & movement",
    "sensorsThatTriggerAlarm": [ "0x31", "0x80"],
    "missingDevicesThatTriggerAlarm": ["0x31", "0x80"],
    "alarmOutputDevices": ["0x99"],
    "alarmTimeLengthSec": 7 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 13,
    "name": "Home/Day - All Alarms Except Garage 10s | Garage Perimeter Sensors",
    "sensorsThatTriggerAlarm": ["0x31", "0x30"],
    "missingDevicesThatTriggerAlarm": ["0x31", "0x30"],
    "alarmOutputDevices": ["0x99", hex(denonId), "0x10"],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 14,
    "name": "Home/Day - Office Alarms 10s | Garage Perimeter Sensors",
    "sensorsThatTriggerAlarm": ["0x31", "0x30"],
    "missingDevicesThatTriggerAlarm": ["0x31", "0x30"],
    "alarmOutputDevices": ["0x99", hex(denonId)],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 15,
    "name": "Office - All Sensors",
    "missingDevicesThatTriggerAlarm": ["0x31", "0x30", "0x75", "0x80", "0x40", "0x50"],
    "alarmOutputDevices": ["0x99"],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 16,
    "name": "Night - Office Alarms 10s | All Garage Sensors",
    "sensorsThatTriggerAlarm": [ "0x31", "0x30", "0x80"],
    "missingDevicesThatTriggerAlarm": ["0x31", "0x30", "0x80"],
    "alarmOutputDevices": ["0x99", hex(denonId)],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 17,
    "name": "Night - Office Alarms 10s | Garage Perimeter Sensors",
    "sensorsThatTriggerAlarm": [ "0x31", "0x30"],
    "missingDevicesThatTriggerAlarm": ["0x31", "0x30"],
    "alarmOutputDevices": ["0x99", hex(denonId)],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 18,
    "name": "Night - Office Alarms 10s | All Sensors",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "alarmOutputDevices": ["0x99", hex(denonId)],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 19,
    "name": "Away - Scary Loud Denon",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "alarmOutputDevices": ["0x99", hex(denonId), "0x10", "0x15"],
    "playSound": "scaryalarm.mp3",
    "playSoundVolume": 65,
    "alarmTimeLengthSec": 30 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 20,
    "name": "All Alarms As Long As Alarmed | All Sensors",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "alarmOutputDevices": ["0x99", "0x15", "0x10", hex(denonId)],
    "alarmTimeLengthSec": 0 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 21,
    "name": "Office and Denon As Long As Alarmed | All Sensors",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "alarmOutputDevices": ["0x99", hex(denonId)],
    "alarmTimeLengthSec": 0 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 22,
    "name": "Office Buzzer As Long As Alarmed | All Sensors",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "alarmOutputDevices": ["0x99"],
    "alarmTimeLengthSec": 0 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "index": 23,
    "name": "Test Denon Only 1s | All Sensors",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30", "0x40", "0x50"],
    "alarmOutputDevices": [hex(denonId)],
    "alarmTimeLengthSec": 1 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}]


###################### MESSAGES #######################
# 0xBB - alarm on signal
# 0xCC - alarm off signal
# 0xD1 - sent to home base arduino - arm 
# 0xD0 - sent to home base arduino - disarm
# 0x0F - power off sensor
# 0x01 - power on sensor
# 0xA0 - sending over to home base arduino (address 0xFF) the address of the alarmed device
# 0xB0 - sending over to home base arduino (address 0xFF) the address of the no longer alarmed device
# 0xC0 - sending over to home base arduino (address 0xFF) stop alarm signal
# 0xEE - arm toggle button on unit pressed

###################### ADDRESSES ######################
#0x00 - broadcast
#0xFF - code for home base's arduino. Message isn't forwarded by arduino to CANBUS.
#0x80 - garage, commercial type (high emmissions, long range)
#0x75 - inside, consumer type (short range)
#0x14 - home base
#0x10 - fire alarm bell
#0x15 - siren alarm
#0x99 - indoor siren with led
#0x30 - door sensor
#0x31 - door sensor
#0xD0 - garage door opener
#0x17 - virtual sensor device that is used to alert people to pick up their phones
#0xDE - virtual test device (sensor)
#0x51 - virtual silence device (alarm, used alone)

#serial message format: 
#   {sender id hex}-{receiver id hex}-{message hex}-{devicetype hex}\n
#when sending to 0x00 (home base arduino)
#   {homeBaseId}-0x00-{message hex}-{message 2 hex}\n

#DEVICE TYPE DICTIONARY:
#01 home base
#02 pir/microwave sensor
#03 bell alarm
#04 visual alarm
#05 door open sensor
#06 device controller
#07 temperature/humidity sensor


ser = serial.Serial('/dev/ttyUSB0', baudrate=115200, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=.25) #quarter second timeout so that Serial.readLine() doesn't block if no message(s) on CAN
print("Arduino: serial connection with PI established")
np.set_printoptions(formatter={'int':hex})

#NEW DEVICES POWER FUNCTION

def setDevicesPower():
    offDevices = []
    onDevices = []
    # if not armed, send OFF to all
    # if armed, send OFF or ON to all depending on whether the device is in the profile's sensorsthattrigger
    if not armed:
        sendPowerCommand([], True, False)
        sendPowerCommand(list(alwaysKeepOnSet), False, True)
    else:
        offDevices, onDevices = getDevicesPowerStateLists()
        sendPowerCommand(offDevices, False, False)
        sendPowerCommand(onDevices, False, True)

def getDevicesPowerStateLists():
    oldProfilesSet = set(memberDevices)
    newProfilesSet = set(alarmProfiles[currentAlarmProfile]['sensorsThatTriggerAlarm']) if 'sensorsThatTriggerAlarm' in alarmProfiles[currentAlarmProfile] else set(memberDevices)

    newProfilesSet = newProfilesSet.union(alwaysKeepOnSet)

    offDevices = list(oldProfilesSet - newProfilesSet)
    onDevices = list(newProfilesSet)

    return offDevices, onDevices


def setCurrentAlarmProfile(profileNumber): #-1 means no profile set. All devices trigger. Alarms are broadcast to all devices.
    global currentAlarmProfile
    global currentlyAlarmedDevices
    global alarmed

    if (profileNumber >= -1 and profileNumber < len(alarmProfiles)):
        currentlyAlarmedDevices = {}
        alarmed = False
        
        currentAlarmProfile = profileNumber
        setDevicesPower()
        sendMessage([homeBaseId, 0x00, 0xCC, 0x01]) #turn off all alarms as part of this change
        print("SETTING ALARM PROFILE " + str(profileNumber) + " - " + getProfileName(profileNumber))
        addEvent({
            "event": "SET PROFILE : " + str(profileNumber) + " - " + getProfileName(profileNumber),
            "time": getReadableTimeFromTimestamp(getTimeSec()),
            "method": "WEB API"
        })
    else:
        print(">>>> PROFILE NUMBER OUT OF RANGE [0," + str(len(alarmProfiles)-1) + "] : " + str(profileNumber))


def addEvent(event):
    global pastEvents
    pastEvents.append(event)


def getArmedStatus():
    return armed

def toggleArmed(now, method):
    global lastArmedTogglePressed
    global alarmed
    global armed
    global memberDevices
    global deviceDictionary
    global everTriggeredWithinAlarmCycle
    global alarmedDevicesInCurrentArmCycle
    global missingDevicesInCurrentArmCycle
    global currentlyAlarmedDevices
    
    lastArmedTogglePressed = now
    if (armed == True):
        print(f">>>>>>>>TURNING OFF ALARM AT {getReadableTimeFromTimestamp(now)} PER {method}<<<<<<<<<")
        addEvent({"event": "DISARMED", "time": getReadableTimeFromTimestamp(now), "method": method})
        armed = False #TODO: add logging of event and source
        alarmed = False #reset alarmed state
        everTriggeredWithinAlarmCycle = {}
        currentlyAlarmedDevices = {}
        alarmedDevicesInCurrentArmCycle = {}
        missingDevicesInCurrentArmCycle = {}
    else:
        print(f">>>>>>>>TURNING ON ALARM AT {getReadableTimeFromTimestamp(now)} PER {method}<<<<<<<<<")
        addEvent({"event": "ARMED", "time": getReadableTimeFromTimestamp(now), "method": method})
        armed = True #TODO: add logging of event and source
        alarmed = False #reset alarmed state
        everTriggeredWithinAlarmCycle = {}
    
    #turn on or off devices depending on armed state
    setDevicesPower()
    sendArmedLedSignal() 
    print("Clearing member devices list")
    resetMemberDevices() #reset all members on the bus when turning on/off


def resetMemberDevices():
    global memberDevices
    memberDevices = {
        hex(denonId): {
            'id': hex(denonId),
            'firstSeen': getTimeSec(),
            'firstSeenReadable': getTimeSec(),
            'deviceType': '0x10',
            'lastSeen': getTimeSec(),
            'lastSeenReadable': getTimeSec(),
            'friendlyName': getFriendlyDeviceName(denonId)
        }
    }


def decodeLine(line):
    try:
        msg = line.split("-")
        msg[3] = msg[3].rstrip('\n')
        msg = [int(i, 16) for i in msg]
    except:
        print(f">>>>ERROR DECODING UTF8 LINE {msg}<<<<<")
        raise("PARSE-ERROR")
    return msg


def encodeLine(message): #[myCanId, addressee, message, myDeviceType]
    printableArr = message.copy()
    printableArr.append(getTimeSec())
    #print("SENDING ", np.array(printableArr)); #TODO: uncomment
    return (hex(message[0]) + "-" + hex(message[1]) + "-" + hex(message[2]) + "-" + hex(message[3]) + "-\n")


def sendMessage(messageArray): 
    global lastSentMessageTimeMsec
    global denonPlayThread
    # global everTriggeredWithinAlarmCycle
    # global mp3AlarmDictionary
    # global currentlyAlarmedDevices

    outgoing = encodeLine(messageArray)
    ser.write(bytearray(outgoing, 'ascii'))
    ser.flushOutput()
    lastSentMessageTimeMsec = getTimeMsec()
    if (messageArray[1] == denonId or messageArray[1] == 0x00):
        if (messageArray[2] == 0xBB and not (denonPlayThread and denonPlayThread.is_alive())):            
            denonPlayThread = Thread(target = playDenonThreadMain, args = (currentlyAlarmedDevices, everTriggeredWithinAlarmCycle, mp3AlarmDictionary))
            denonPlayThread.start()


def getCurrentProfileSoundByteData():
    playSoundVolume = -1
    playSound = ""

    for index, profile in enumerate(alarmProfiles):
        print(">>>>>> PROFILE INDEX " + str(index))
        if (index != currentAlarmProfile):
            continue
        if ('playSound' in profile and profile['playSound']):
            playSound = profile['playSound']
        if ('playSoundVolume' in profile and profile['playSoundVolume']):
            playSoundVolume = profile['playSoundVolume']
    print(">>>>>>> PLAYSOUND " + playSound)
    print(">>>>>>> PLAYSOUNDVOLUME " + str(playSoundVolume))
    return playSound, playSoundVolume


def getThisDirAddress():
    return os.path.dirname(__file__)


def getTime():
    return datetime.now().timestamp()
    #return math.floor(datetime.now(timezone('US/Pacific')).timestamp())


def getTimeSec():
    return math.floor(getTime())


def getTimeMsec():
    return math.floor(getTime()*1000)


def getReadableTime():
    return getReadableTimeFromTimestamp(getTimeSec())


def getReadableTimeFromTimestamp(timestamp):
    return f"{datetime.fromtimestamp(timestamp).strftime('%c')} LOCAL TIME"


def possiblyAddMember(msg):
    global memberDevices
    now = getTimeSec()
    if (msg[0] != homeBaseId):
        readableTimestamp = getReadableTime()

        if (hex(msg[0]) not in memberDevices) :
            print(f"Adding new device to members list {hex(msg[0])} at {readableTimestamp}")
            addEvent({"event": "NEW_MEMBER", "trigger": hex(msg[0]), "time": readableTimestamp})
            memberDevices[hex(msg[0])] = {
                'id': hex(msg[0]),
                'firstSeen': now,
                'firstSeenReadable': readableTimestamp,
                'deviceType': msg[3],
                'lastSeen': now,
                'lastSeenReadable': readableTimestamp,
                'friendlyName': getFriendlyDeviceName(msg[0])
            }
        else :
            memberDevices[hex(msg[0])]['lastSeen'] = now
            memberDevices[hex(msg[0])]['lastSeenReadable'] = readableTimestamp


def playDenonThreadMain(currentlyAlarmedDevices, everAlarmedDuringAlarm, mp3AlarmDictionary):
    cwd = getThisDirAddress()
    playCommandArray = ["/usr/bin/mpg123"]
    volume = "55" #default

    ####types of sounds####
    #test sound from testAlarmId
    #pick up your phones from checkPhonesId
    #sound byte override
    #fall back to saying the sensors that are activated

    playCommandArray, volume = determineStuffToPlay(playCommandArray, volume, everAlarmedDuringAlarm, currentlyAlarmedDevices)
    startPowerStatus, startChannelStatus, startVolume = getDenonInitialState(cwd)
    if (startPowerStatus == False and startChannelStatus == False and startVolume == False):
        return
    setDenonPlayState(startPowerStatus, startChannelStatus, volume, cwd)
    playDenonSounds(playCommandArray, cwd)
    setDenonOriginalState(startPowerStatus, startChannelStatus, startVolume, cwd)


def determineStuffToPlay(playCommandArray, volume, everAlarmedDuringAlarm, currentlyAlarmedDevices):
    sound = ""
    #playCommandArray.append("./alert.mp3")

    if (hex(testAlarmId) in currentlyAlarmedDevices):
        sound = "thisisatest.mp3"
        currentlyAlarmedDevices.pop(hex(testAlarmId));
    elif (hex(checkPhonesId) in currentlyAlarmedDevices):
        sound = "checkyourphones.mp3"
        volume = "79"
        currentlyAlarmedDevices.pop(hex(checkPhonesId));
    else:
        playCommandArray.append("./alert.mp3")
        soundByteOverride, volumeOverride = getCurrentProfileSoundByteData()
        if (soundByteOverride and volumeOverride):
            volume = volumeOverride
            sound = soundByteOverride
    
    #if special case sound found above, use it
    if (sound):
        playCommandArray.append(sound)
    #otherwise, play names of sensors active
    else:
        for device in everAlarmedDuringAlarm:
            resolvedMp3 = mp3AlarmDictionary[device]
            if (resolvedMp3):
                playCommandArray.append(resolvedMp3)
        #playCommandArray.append('compromised.mp3')

    return playCommandArray, volume


def playDenonSounds(playCommandArray, cwd):
    #play sound(s) 
    subprocess.run(
        playCommandArray, 
        cwd=cwd
    )


def setDenonPlayState(startPowerStatus, startChannelStatus, volume, cwd):
    #turn on and switch to $avrSoundChannel if previously off OR previously channel isn't $avrSoundChannel;
    #then sleep the appropriate number of seconds to let denon get ready 
    if (startPowerStatus != 'ON' or startChannelStatus != avrSoundChannel):
        subprocess.run("./denonon.sh", cwd=cwd)
        time.sleep(8 if startPowerStatus != 'ON' else 3)
    
    #set volume
    subprocess.run(["./denonvol.sh", str(volume)], cwd=str(cwd))


def setDenonOriginalState(startPowerStatus, startChannelStatus, startVolume, cwd):
    #turn off if was off before
    if (startPowerStatus != 'ON'): #TODO: add condition: and the alarm has been canceled
        subprocess.run(os.path.dirname(__file__) + "/denonoff.sh", cwd=cwd)
    #otherwise, set volume to old volume
    else :
        subprocess.run(["./denonvol.sh", startVolume], cwd=cwd)
        if (startChannelStatus != avrSoundChannel):
            subprocess.run(["./denonchannel.sh", startChannelStatus], cwd=cwd)


def getDenonInitialState(cwd):
    #store original power status
    startPowerStatus = str(
        subprocess.run("./denonpowerstatus.sh", cwd=cwd, stderr=None, capture_output=True).stdout
        ).translate({ord(c): None for c in 'b\\n\''})

    #if cannot find denon, cannot play -> exit thread
    if (startPowerStatus == ''):
        print('>>>>DENON NOT FOUND')
        return False, False, False #signals quit now

    #store original channel
    startChannelStatus = str(
        subprocess.run("./denonchannelstatus.sh", cwd=cwd, stderr=None, capture_output=True).stdout
        ).translate({ord(c): None for c in 'b\\n\''})

    #store original volume    
    tempvol = str(
        subprocess.run("./denonvolumestatus.sh", cwd=cwd, stderr=None, capture_output=True).stdout
        ).translate({ord(c): None for c in 'b\\n\''})
    if (tempvol == '--'):
        tempvol = '0'

    startVolume = str(int(float(tempvol)+81))

    return startPowerStatus, startChannelStatus, startVolume


def getFriendlyDeviceName(address):
    strAddress = hex(address)
    return deviceDictionary[strAddress] if strAddress in deviceDictionary else "unlisted"


def getFriendlyDeviceNamesFromDeviceDictionary(dict):
    friendlyDeviceNames = []
    for key in dict:
        if key in deviceDictionary:
            friendlyDeviceNames.append(deviceDictionary[key])
        else:
            friendlyDeviceNames.append("unknown " + key)
    return friendlyDeviceNames;


def checkMembersOnline():
    now = getTimeSec()
    global lastCheckedMissingDevicesMsec
    global missingDevicesInCurrentArmCycle
    lastCheckedMissingDevicesMsec = getTimeMsec()
    missingMembers = []
    for memberId in memberDevices :
        if (not memberId in exceptMissingDevices and memberDevices[memberId]['lastSeen'] + deviceAbsenceThresholdSec < now) :
            print(f"Adding missing device {memberId} at {getReadableTime()}. missing for {(getTimeSec()-memberDevices[memberId]['lastSeen'])} seconds")
            missingMembers.append(memberId)
            everMissingDevices[memberId] = True;
            missingDevicesInCurrentArmCycle[memberId] = now
    return missingMembers


def sendArmedLedSignal():
    if (armed == True):
        messageToSend = [homeBaseId, 0xFF, 0xD1, 0x01]
        print(f">>>> SENDING ARM SIGNAL TO ARDUINO {np.array(messageToSend)}")
    else:
        messageToSend = [homeBaseId, 0xFF, 0xD0, 0x01]
        print(f">>>> SENDING DISARM SIGNAL TO ARDUINO {np.array(messageToSend)}")
    sendMessage(messageToSend)


#by default, sends to all members of current profile, unless overridden with at most 1 of the first 2 params
def sendPowerCommand(devicesOverrideArray, shouldBroadcast, powerState): #two op
    # global memberDevices
    # global currentAlarmProfile
    # global alarmProfiles
    
    devicesToSendTo = devicesOverrideArray if devicesOverrideArray else memberDevices if shouldBroadcast else alarmProfiles[currentAlarmProfile]["sensorsThatTriggerAlarm"] if "sensorsThatTriggerAlarm" in alarmProfiles[currentAlarmProfile] else memberDevices
    for member in devicesToSendTo:
        intMemberId = int(member, 16)
        messageToSend = [homeBaseId, intMemberId, 0x0F if powerState else 0x01, 0x01]
        sendMessage(messageToSend) #stand up power - 0x0F enabled / 0x01 disabled
        print(f">>>> SENDING POWER {'ON' if powerState else 'OFF'} SIGNAL {np.array(messageToSend)}")
        time.sleep(.25) #in seconds, double - 500 msec sleep


def exitSteps():
    print(f"\n\nEXITING AT {getReadableTime()}")
    print("BROADCASTING QUIET-ALL-ALARMS SIGNAL")
    sendMessage([homeBaseId, 0x00, 0xCC, 0x01]) #reset all devices (broadcast)
    print("BROADCASTING ALL-SENSOR-DEVICES-OFF SIGNAL")
    sendMessage([homeBaseId, 0x00, 0x01, 0x01]) #all devices off (broadcast)
    print("\nPAST EVENTS LIST FOLLOWS:")
    for line in pastEvents:
        print(f"\t{line}")    


def arrayToString(array):
    string = ""
    for i in array:
        string += "" + i + " "
    return string


def handleMessage(msg):
    if (debug):
        print(f"SENDER {hex(msg[0])} RECEIVER {hex(msg[1])} MESSAGE {hex(msg[2])} DEVICE-TYPE {hex(msg[3])}")

    possiblyAddMember(msg)
    global alarmed
    global homeBaseId
    global lastAlarmTime
    global armed
    global lastArmedTogglePressed
    global alarmReason
    global currentlyAlarmedDevices
    global everTriggeredWithinAlarmCycle
    global alarmedDevicesInCurrentArmCycle
    global currentAlarmProfile
    global canDebugMessage
    global shouldSendDebugRepeatedly
    global shouldSendDebugMessage

    now = getTimeSec()

    #if we are faking output from a certain device, ignore all messages from that device and replace with 
    if (shouldSendDebugMessage and msg[0] == canDebugMessage[0]):
        msg = canDebugMessage
        if (not shouldSendDebugRepeatedly):
            shouldSendDebugMessage = False
            canDebugMessage = []

    #for some messages - handle special cases intended for this unit from arduino, and return; if not, drop down to handle general case logic block
    if (msg[0]==homeBaseId and msg[1]==homeBaseId and msg[2]==0xEE and lastArmedTogglePressed < now): 
        toggleArmed(now, "ARDUINO")
        return

    #alarm message coming in from a device that isn't in the currentlyAlarmedDevices list
    if ((msg[1]==homeBaseId or msg[1]==broadcastId) and msg[2]==0xAA and hex(msg[0]) not in currentlyAlarmedDevices) :
        currentlyAlarmedDevices[hex(msg[0])] = now;
        if (not "sensorsThatTriggerAlarm" in alarmProfiles[currentAlarmProfile] or ("sensorsThatTriggerAlarm" in alarmProfiles[currentAlarmProfile] and hex(msg[0]) in alarmProfiles[currentAlarmProfile]["sensorsThatTriggerAlarm"])): #either all alarms trigger (sensorsThatTriggerAlarm missing from profile) OR current device ID in sensorsThatTriggerAlarm
            print(f">>>>>>>>>>>>>>>>>RECEIVED TRIGGER SIGNAL FROM {hex(msg[0])} AT {getReadableTime()}<<<<<<<<<<<<<<<<<<")
            if (armed): 
                alarmed = True
                lastAlarmTime = now;
                alarmedDevicesInCurrentArmCycle[hex(msg[0])] = now;
                everTriggeredWithinAlarmCycle[hex(msg[0])] = now;
                updateCurrentlyTriggeredDevices();
                addEvent({"event": "TRIGGERED-ALARM", "trigger": alarmReason, "time": getReadableTimeFromTimestamp(lastAlarmTime)})
                print (f">>>>>currentAlarmProfile {currentAlarmProfile}")
                sendMessage([homeBaseId, 0xFF, 0xA0, msg[0]]) #send to the home base's arduino a non-forwardable message with the ID of the alarm-generating device to be added to the list
            else:
                addEvent({"event": "TRIGGERED-NO-ALARM", "trigger": hex(msg[0]), "time": getReadableTimeFromTimestamp(now)})
        else:
            addEvent({"event": "TRIGGERED-NO-ALARM", "trigger": hex(msg[0]), "time": getReadableTimeFromTimestamp(now)})

    #a no-alarm message is coming in from a device that is in the alarmed device list
    elif ((msg[1]==homeBaseId or msg[1]==broadcastId) and msg[2]==0x00 and hex(msg[0]) in currentlyAlarmedDevices):
        print(f"DEVICE {hex(msg[0])} NO LONGER IN currentlyAlarmedDevices - MESSAGE TO REMOVE FROM OLED")
        #home base's arduino should not show this device's ID as one that is currently alarmed
        currentlyAlarmedDevices.pop(hex(msg[0]))
        addEvent({"event": "TRIGGER-STOPPED", "trigger": hex(msg[0]), "time": getReadableTimeFromTimestamp(now)})
        sendMessage([homeBaseId, 0xFF, 0xB0, msg[0]])
        updateCurrentlyTriggeredDevices();


def updateCurrentlyTriggeredDevices():
    global alarmReason
    global currentlyAlarmedDevices
    global currentlyMissingDevices

    alarmReason = ""
    for missingId in currentlyMissingDevices:
        alarmReason += ("" if not alarmReason else " ") + "missing " + missingId
    for alarmedId in currentlyAlarmedDevices:
        alarmReason += ("" if not alarmReason else " ") + "tripped " + alarmedId
    if (debug): print("Updated alarm reason to: " + alarmReason)


def getProfilesJsonString():
    global alarmProfiles

    profilesJSON = ""
    for profile in alarmProfiles:
        profilesJSON += json.dumps(profile) + ","
    profilesJSON = profilesJSON[:-1]

    strReturn = '{"profiles": [' + profilesJSON + ']}'
    return strReturn


def getStatusJsonString():
    strAlarmedStatus = "ALARM" if alarmed else "NORMAL"
    outgoingMessage = '{"armStatus": "' + ("ARMED" if armed else "DISARMED") + '",'
    outgoingMessage += '"alarmStatus": "' + strAlarmedStatus + '",'
    outgoingMessage += '"garageOpen": ' + ('true' if hex(garageDoorSensorId) in currentlyAlarmedDevices else 'false') + ','
    outgoingMessage += '"profile": "' + alarmProfiles[currentAlarmProfile]["name"] + '",'
    outgoingMessage += '"profileNumber": "' + str(currentAlarmProfile) + '",'
    outgoingMessage += '"currentTriggeredDevices": ' + str(list(currentlyAlarmedDevices.keys())).replace("'","\"") + ","
    outgoingMessage += '"currentMissingDevices": ' + str(currentlyMissingDevices).replace("'","\"") + ','
    outgoingMessage += '"everTriggeredWithinAlarmCycle": ' + str(list(everTriggeredWithinAlarmCycle.keys())).replace("'","\"") + ","
    outgoingMessage += '"everTriggeredWithinArmCycle": ' + str(list(alarmedDevicesInCurrentArmCycle.keys())).replace("'","\"") + ","
    outgoingMessage += '"everMissingWithinArmCycle": ' + str(list(missingDevicesInCurrentArmCycle.keys())).replace("'","\"") + ","
    outgoingMessage += '"everMissingDevices": ' + str(list(everMissingDevices.keys())).replace("'","\"") + ","
    outgoingMessage += '"memberCount": ' + str(len(memberDevices)) + ','
    outgoingMessage += '"memberDevices": ' + str(list(memberDevices.keys())).replace("'","\"") + ','
    outgoingMessage += '"memberDevicesReadable": ' + str(getFriendlyDeviceNamesFromDeviceDictionary(list(memberDevices.keys()))).replace("'","\"")
    outgoingMessage += '}'
    return outgoingMessage


def getPastEventsJsonString():
    outgoingMessage = '{"pastEvents": ' + str(pastEvents).replace("'","\"")
    outgoingMessage += '}'
    return outgoingMessage


def stopAlarm():
    global alarmed
    global lastAlarmTime
    global everTriggeredWithinAlarmCycle
    global currentlyAlarmedDevices
    global homeBaseId

    alarmed = False
    addEvent({"event": "FINISHED_ALARM", "time": getReadableTimeFromTimestamp(lastAlarmTime)})
    everTriggeredWithinAlarmCycle = {}
    currentlyAlarmedDevices = {}
    updateCurrentlyTriggeredDevices()
    sendMessage([homeBaseId, 0xFF, 0xC0, 0x01])


def run(webserver_message_queue):
    global LISTEN_PORT
    global memberDevices
    global currentlyAlarmedDevices
    global everTriggeredWithinAlarmCycle
    global homeBaseId
    global pastEvents
    global alarmed
    global lastAlarmTime
    global armed
    global lastArmedTogglePressed
    global deviceAbsenceThresholdSec
    global firstPowerCommandNeedsToBeSent
    global timeAllottedToBuildOutMembersSec
    global initWaitSeconds
    global lastSentMessageTimeMsec
    global sendTimeoutMsec
    global currentlyMissingDevices
    global checkForMissingDevicesEveryMsec
    global lastCheckedMissingDevicesMsec
    global alarmProfiles
    global currentAlarmProfile
    global alwaysKeepOnSet
    global testAlarmId
    global missingDevices
    resetMemberDevices()

    atexit.register(exitSteps)
    print(f"STARTING ALARM SCRIPT AT {getReadableTimeFromTimestamp(getTimeSec())}.\nWAITING {initWaitSeconds} SECONDS TO SET UP SERIAL BUS...")
    time.sleep(initWaitSeconds)
    print(f"DONE WAITING, OPERATIONAL NOW AT {getReadableTimeFromTimestamp(getTimeSec())}. STATUS:\nARMED: {armed}\nALARMED: {alarmed}\n\n\n")

    ser.flushOutput()
    ser.flushInput()
    sendMessage([homeBaseId, 0x00, 0xCC, 0x01]) #reset all devices (broadcast)
    sendArmedLedSignal()
    firstTurnedOnTimestamp = getTimeSec()

    while True:
        line = ser.readline()
        if not webserver_message_queue.empty():
            message = webserver_message_queue.get()
            #print(f"GOT MESSAGE: {message}")
            if (message['request'] == "ENABLE-ALARM" and getArmedStatus() == False) :
                toggleArmed(getTimeSec(), "WEB API")
            elif (message['request'] == "DISABLE-ALARM" and getArmedStatus() == True) :
                toggleArmed(getTimeSec(), "WEB API")
            elif (message['request'] == "ALARM-STATUS") :
                message['responseQueue'].put({"response": getStatusJsonString(), "uuid": message['uuid'] })
            elif (message['request'].startswith("SET-ALARM-PROFILE-")):
                profileNumber = int(message['request'].split("SET-ALARM-PROFILE-",1)[1])
                setCurrentAlarmProfile(profileNumber)
            elif (message['request'] == "GET-ALARM-PROFILES") :
                message['responseQueue'].put({"response": getProfilesJsonString(), "uuid": message['uuid'] })
            elif (message['request'] == "FORCE-ALARM-SOUND-ON") :
                currentlyAlarmedDevices[hex(testAlarmId)] = getTimeSec();
                sendAlarmMessage(True, True)
                time.sleep(.15)
                sendAlarmMessage(False, False)
            elif (message['request'] == "TOGGLE-GARAGE-DOOR-STATE") :
                sendMessage([homeBaseId, garageDoorOpenerId, 0x0D, 0x00])
            elif (message['request'] == "CLEAR-OLD-DATA") :
                clearOldData()
            elif (message['request'] == "ALERT-CHECK-PHONES") :
                currentlyAlarmedDevices[hex(checkPhonesId)] = getTimeSec();
                sendAlarmMessage(True, True)
                time.sleep(.1)
                sendAlarmMessage(False, False)
            elif (message['request'].startswith("CAN-REPEATEDLY-SEND-")) :
                sendcan(message['request'].split('CAN-REPEATEDLY-SEND-')[1], True)
            elif (message['request'].startswith("CAN-SINGLE-SEND-")) :
                sendcan(message['request'].split('CAN-SINGLE-SEND-')[1], False)
            elif (message['request'] == "CAN-STOP-SENDING") :
                stopsendingcan()
            elif (message['request'] == "GET-PAST-EVENTS") :
                message['responseQueue'].put({"response": getPastEventsJsonString(), "uuid": message["uuid"] })


        if (not line): continue #nothing on CAN -> repeat while loop (since web server message is already taken care of above)
        
        ser.flushInput()

        if (firstPowerCommandNeedsToBeSent and getTimeSec() > firstTurnedOnTimestamp + timeAllottedToBuildOutMembersSec):
            firstPowerCommandNeedsToBeSent = False
            print(f"Members array built at {getReadableTimeFromTimestamp(getTimeSec())} as:")
            for member in memberDevices:
                print(f"{member} : {memberDevices[member]}")
            print("\n\n\n")
            sendPowerCommand([], True, False) #turn off all - broadcast
            sendPowerCommand(set(alwaysKeepOnSet), False, True) #turn on those devices that are meant to stay on always
        try:
            decodedLine = line.decode('utf-8')
        except:
            print(f">>>>>ERROR ON BUS WHILE PARSING MESSAGE //// SKIPPING THIS MESSAGE<<<<<<")
            continue
        if (decodedLine.startswith(">>>")): #handle debug lines over serial without crashing
            #print(line.decode('utf-8'))
            continue
        try:
            msg = decodeLine(decodedLine)
        except:
            print(f"ERROR WITH PARSING LINE, CONTINUING LOOP<<<<<")
            continue
        msg.append(getTimeSec())
        #print("GETTING", np.array(msg)) #TODO: uncomment

        handleMessage(msg)


        if (lastCheckedMissingDevicesMsec+checkForMissingDevicesEveryMsec < getTimeMsec()):  #do a check for missing devices
            if (debug): 
                print(f">>>Checking for missing devices at {getTimeMsec()}")
            missingDevices = checkMembersOnline()

            if (armed and len(currentlyMissingDevices) > 0):
                updateCurrentlyTriggeredDevices()
                print(f">>>>>>>>>>>>>>>>>>>> ADDING MISSING DEVICES {arrayToString(currentlyMissingDevices)} at {getReadableTime()}<<<<<<<<<<<<<<<<<<<")
                shouldSetNewAlarm = False;
                for missingDevice in currentlyMissingDevices:
                    if (not "missingDevicesThatTriggerAlarm" in alarmProfiles[currentAlarmProfile] or missingDevice in alarmProfiles[currentAlarmProfile]["missingDevicesThatTriggerAlarm"]):
                        shouldSetNewAlarm = True
                        break;
                if (shouldSetNewAlarm):
                    alarmed = True
                    lastAlarmTime = getTimeSec()
                    addEvent({"event": "DEVICE-MISSING-ALARM", "trigger": alarmReason, "time": getReadableTimeFromTimestamp(lastAlarmTime)})
                else :
                    addEvent({"event": "DEVICE-MISSING-NOALARM", "trigger": alarmReason, "time": getReadableTimeFromTimestamp(lastAlarmTime)})

        #if currently alarmed and there are no missing or alarmed devices and it's been long enough that alarmTimeLengthSec has run out, DISABLE ALARM FLAG
        if (alarmed and getCurrentProfileAlarmTime() > -1 and lastAlarmTime + getCurrentProfileAlarmTime() < getTimeSec() and len(currentlyMissingDevices) == 0 and len(currentlyAlarmedDevices) == 0):
            stopAlarm()
            updateCurrentlyTriggeredDevices()

        else:
            updateCurrentlyTriggeredDevices()

        #possibly send a message (if it's been sendTimeoutMsec)
        if (getTimeMsec() > (lastSentMessageTimeMsec+sendTimeoutMsec)):
            sendAlarmMessage(armed, alarmed)


def sendAlarmMessage(armed, alarmed):
    global currentAlarmProfile
    global alarmProfiles
    global homeBaseId
    if ("alarmOutputDevices" in alarmProfiles[currentAlarmProfile] and armed and alarmed): #send alarms to chosen devices under this profile (non-default profile)
        for deviceToBeAlarmed in alarmProfiles[currentAlarmProfile]["alarmOutputDevices"]:
            sendMessage([homeBaseId, int(deviceToBeAlarmed, 16), 0xBB , 0x01])
            time.sleep(5/100) #bugfix - can't send in immediate rapid succession, or can fails
    elif ("alarmOutputDevices" in alarmProfiles[currentAlarmProfile]): #send cancel alarms to all devices under this profile (non-default profile)
        for deviceToBeAlarmed in alarmProfiles[currentAlarmProfile]["alarmOutputDevices"]:
            sendMessage([homeBaseId, int(deviceToBeAlarmed, 16), 0xCC , 0x01])
            time.sleep(5/100) #bugfix - can't send in immediate rapid succession, or can fails
    else: # for profiles missing alarmOutputDevices - broadcast alarm on or off
        sendMessage([homeBaseId, 0x00, 0xBB if armed and alarmed else 0xCC, 0x01])


def getCurrentProfileAlarmTime():
    global alarmProfiles
    global currentAlarmProfile
    return alarmProfiles[currentAlarmProfile]["alarmTimeLengthSec"]


def getProfileName(profileNumber):
    global alarmProfiles
    return alarmProfiles[profileNumber]["name"]


def clearOldData():
    global everTriggeredWithinAlarmCycle
    global alarmedDevicesInCurrentArmCycle
    global missingDevicesInCurrentArmCycle
    global everMissingDevices
    global currentlyMissingDevices
    global pastEvents

    everTriggeredWithinAlarmCycle = {}
    alarmedDevicesInCurrentArmCycle = {}
    missingDevicesInCurrentArmCycle = {}
    everMissingDevices = {}
    currentlyMissingDevices = []
    pastEvents = []
    resetMemberDevices()


def stopsendingcan():
    global canDebugMessage
    global shouldSendDebugRepeatedly
    global shouldSendDebugMessage
    global currentlyAlarmedDevices

    canDebugMessage = []
    shouldSendDebugRepeatedly = False
    shouldSendDebugMessage = False
    currentlyAlarmedDevices = {}

    print('STOPPING SENDING FAKE MESSAGE FROM UI')
    addEvent({
        "event": "STOPPING SENDING DEBUG CAN MESSAGE FROM UI",
        "time": getReadableTimeFromTimestamp(getTimeSec()),
        "method": "WEB API"
    })


def sendcan(message, repeatedly):
    global canDebugMessage
    global shouldSendDebugRepeatedly
    global shouldSendDebugMessage
    messageConforms = True

    arrCanDebugMessage = message.split(':')
    if (len(arrCanDebugMessage) == 4):
        for index, i in enumerate(arrCanDebugMessage):
            if not i.startswith('0x') or len(i) != 4:
                messageConforms = False
                break
            else:
                arrCanDebugMessage[index]=int(i, 16)
        if messageConforms:
            print('SENDING FAKE MESSAGE FROM UI ' + str(arrCanDebugMessage) + (" REPEATEDLY " if repeatedly else ""))
            addEvent({
                "event": "STARTING SENDING DEBUG CAN MESSAGE " + str(arrCanDebugMessage) + " FROM UI" + (" REPEATEDLY" if repeatedly else ""),
                "time": getReadableTimeFromTimestamp(getTimeSec()),
                "method": "WEB API"
            })
            canDebugMessage = arrCanDebugMessage
            shouldSendDebugRepeatedly = True if repeatedly else False
            shouldSendDebugMessage = True

#TODO: 
#ADJUST AND FLASH ALL DEVICES WITH CORRECT DEVICETYPES!!
#web server certs auth
#profiles
#profiles with trigger conditions and overridable default alarm (specific-device alarms)
#overlapping profiles (multiple alarm sessions at the same time)
#rename variables
#long antenna for key fob
#remote garage opener
#light alarm 24v
#wire the wall
#power things for any device with relay into 5v


#pmd.reset_output_buffer()


if __name__ == "__main__":
    run(None)  # For testing in standalone mode

