import serial
from datetime import datetime, timezone, timedelta
import math
import numpy as np
import time
import atexit
import tornado.ioloop
import tornado.web
import json
import subprocess
import os
from threading import Thread



debug = False
LISTEN_PORT=8080
ser = serial.Serial('/dev/ttyUSB0', baudrate=115200, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=.25) #quarter second timeout so that Serial.readLine() doesn't block if no message(s) on CAN
print("Arduino: serial connection with PI established")
memberDevices = {} #map of {string hex id:{properties}}
denonId = 0x33
garageDoorOpenerId = 0xD0
garageDoorSensorId = 0x30
exceptMissingDevices = {hex(denonId): True, hex(garageDoorOpenerId): True}
deviceDictionary = {
    "0x80": "garage motion sensor 0x80",
    "0x75": "inside motion sensor 0x75",
    hex(garageDoorSensorId): "garage car door sensor " + hex(garageDoorSensorId),
    "0x31": "garage side door sensor 0x31",
    "0x14": "home base",
    "0xFF": "home base communicating to its arduino",
    "0x10": "fire alarm bell 0x10",
    "0x15": "piezo 120db alarm 0x15",
    "0x99": "office led and buzzer 0x99",
    hex(denonId): "denon via curl " + hex(denonId),
    hex(garageDoorOpenerId): "garage door opener " + hex(garageDoorOpenerId)
}
mp3AlarmDictionary = {
    "0x80": "garagemovement.mp3",
    "0x75": "indoormovement.mp3",
    hex(garageDoorSensorId): "garagedoor.mp3",
    "0x31": "garagesidedoor.mp3",
    "0x17": "checkyourphones.mp3"
}
denonPlayThread = 0
alarmProfiles = [{
    "name": "Default - all sensors / all alarms / 5s", #all missing and all triggers BROADCAST ALARM
    "alarmTimeLengthSec": 5 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)

}, {
    "name": "Night - all sensors / office alarm only / 10s",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30"],
    "alarmOutputDevices": ["0x99"],
    "alarmTimeLengthSec": 10 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "name": "Away - all sensors / all alarms / 30s",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30"],
    "alarmOutputDevices": ["0x99", "0x15", "0x10", hex(denonId)],
    "alarmTimeLengthSec": 30 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "name": "All sensors / all alarms / as long as alarmed",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30"],
    "alarmOutputDevices": ["0x99", "0x15", "0x10", hex(denonId)],
    "alarmTimeLengthSec": 0 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "name": "All sensors / office alarm only / as long as alarmed",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30"],
    "alarmOutputDevices": ["0x99"],
    "alarmTimeLengthSec": 0 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}, {
    "name": "All sensors / office and denon / as long as alarmed",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30"],
    "alarmOutputDevices": ["0x99", hex(denonId)],
    "alarmTimeLengthSec": 0 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
}]
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

#serial message format: 
#   {sender id hex}-{receiver id hex}-{message hex}-{devicetype hex}\n
#when sending to 0x00 (home base arduino)
#   {homeBaseId}-0x00-{message hex}-{message 2 hex}\n

#DEVICE TYPE DICTIONARY:
#01 controller
#02 pir/microwave sensor
#03 bell alarm
#04 visual alarm
#05 door open sensor


np.set_printoptions(formatter={'int':hex})

def setCurrentAlarmProfile(profileNumber): #-1 means no profile set. All devices trigger. Alarms are broadcast to all devices.
    global currentAlarmProfile
    global alarmProfiles
    if (profileNumber >= -1 and profileNumber < len(alarmProfiles)):
        currentAlarmProfile = profileNumber
    print("SETTING ALARM PROFILE " + str(profileNumber) + " - " + getProfileName(profileNumber))
    addEvent({
        "event": "SET PROFILE : " + str(profileNumber) + " - " + getProfileName(profileNumber),
        "time": getReadableTimeFromTimestamp(getTimeSec()),
        "method": "WEB API"
    })
    sendMessage([homeBaseId, 0x00, 0xCC , 0x01]) #turn off all alarms as part of this change


def addEvent(event):
    global pastEvents
    pastEvents.append(event)


def getArmedStatus():
    global armed
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
    
    
    sendPowerCommandDependingOnArmedState() 
    sendArmedLedSignal() 
    print("Clearing member devices list")
    resetMemberDevices() #reset all members on the bus when turning on/off

def resetMemberDevices():
    global memberDevices
    global denonId
    now = getTimeSec()
    readableTimestamp = getReadableTime()
    memberDevices = {
        hex(denonId): {
            'id': hex(denonId),
            'firstSeen': now,
            'firstSeenReadable': readableTimestamp,
            'deviceType': '0x10',
            'lastSeen': now,
            'lastSeenReadable': readableTimestamp,
            'friendlyName': getFriendlyName(denonId)
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
    global currentlyAlarmedDevices
    global mp3AlarmDictionary
    outgoing = encodeLine(messageArray)
    ser.write(bytearray(outgoing, 'ascii'))
    ser.flushOutput()
    lastSentMessageTimeMsec = getTimeMsec()
    if (messageArray[1] == denonId or messageArray[1] == 0x00):
        if (messageArray[2] == 0xCC):
            print('DENON ALARM OFF')
            
        elif (messageArray[2] == 0xBB and not (denonPlayThread and denonPlayThread.is_alive())):
            denonPlayThread = Thread(target = playDenon, args = (currentlyAlarmedDevices, mp3AlarmDictionary, ))
            denonPlayThread.start()
    
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
                'friendlyName': getFriendlyName(msg[0])
            }
        else :
            memberDevices[hex(msg[0])]['lastSeen'] = now
            memberDevices[hex(msg[0])]['lastSeenReadable'] = readableTimestamp

def playDenon(currentlyAlarmedDevices, mp3AlarmDictionary):
    directory = getThisDirAddress()
    playCommandArray = ["/usr/bin/mpg123", "./alert.mp3"]
    added = False

    for device in currentlyAlarmedDevices:
        print('>>>>>>>' + device)
        resolvedMp3 = mp3AlarmDictionary[device]
        if (resolvedMp3):
            playCommandArray.append(resolvedMp3)
            added = True

    if (not added):
        playCommandArray.append("./thisisatest.mp3")
    if (added and not "checkyourphones.mp3" in playCommandArray ):
        playCommandArray.append("./compromised.mp3")

    startPowerStatus = str(
        subprocess.run("./denonpowerstatus.sh", cwd=directory, stderr=None, capture_output=True).stdout
        ).translate({ord(c): None for c in 'b\\n\''})

    myvol = str(
        subprocess.run("./denonvolumestatus.sh", cwd=directory, stderr=None, capture_output=True).stdout
        ).translate({ord(c): None for c in 'b\\n\''})
    if (myvol == '--'):
        myvol = '0'

    startVolume = str(int(float(myvol)+81))
    
    if (not startPowerStatus == 'ON'):
        subprocess.run("./denonon.sh", cwd=directory)
    
    subprocess.run(["./denonvol.sh", "50" if not "checkyourphones.mp3" in playCommandArray else "70"], cwd=directory)
    if (not startPowerStatus == 'ON'):
        time.sleep(8) #enough time for Denon to turn on and warm up
    subprocess.run(
        playCommandArray, 
        cwd=directory
    )
    if (not startPowerStatus == 'ON'): #TODO: add condition: and the alarm has been canceled
        subprocess.run(os.path.dirname(__file__) + "/denonoff.sh", cwd=directory)
    else :
        subprocess.run(["./denonvol.sh", startVolume], cwd=directory)

def getFriendlyName(address):
    strAddress = hex(address)
    return deviceDictionary[strAddress] if strAddress in deviceDictionary else "unlisted"


def getFriendlyNamesFromDeviceDict(dict):
    friendlyDeviceNames = []
    for key in dict:
        if key in deviceDictionary:
            friendlyDeviceNames.append(deviceDictionary[key])
    return friendlyDeviceNames;


def checkMembersOnline():
    now = getTimeSec()
    global lastCheckedMissingDevicesMsec
    global missingDevicesInCurrentArmCycle
    global exceptMissingDevices
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
    global armed
    if (armed == True):
        messageToSend = [homeBaseId, 0xFF, 0xD1, 0x01]
        print(f">>>> SENDING ARM SIGNAL TO ARDUINO {np.array(messageToSend)}")
    else:
        messageToSend = [homeBaseId, 0xFF, 0xD0, 0x01]
        print(f">>>> SENDING DISARM SIGNAL TO ARDUINO {np.array(messageToSend)}")
    sendMessage(messageToSend)


def sendPowerCommandDependingOnArmedState():
    global memberDevices
    global homeBaseId
    global armed
    if (armed == False):
        messageToSend = [homeBaseId, 0x00, 0x01, 0x01]
        sendMessage(messageToSend) #stand down power - 0x0F enabled / 0x01 disabled
        print(f">>>> BROADCASTING POWER OFF SIGNAL {np.array(messageToSend)}")
    else:
        for member in memberDevices:
            intMemberId = int(member, 16)
            messageToSend = [homeBaseId, intMemberId, 0x0F, 0x01]
            sendMessage(messageToSend) #stand up power - 0x0F enabled / 0x01 disabled
            print(f">>>> SENDING POWER ON SIGNAL {np.array(messageToSend)}")
            time.sleep(1/2) #in seconds, double - 500 msec sleep


def exitSteps():
    global pastEvents
    global homeBaseId
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
    global pastEvents
    global homeBaseId
    global lastAlarmTime
    global armed
    global lastArmedTogglePressed
    global memberDevices
    global alarmReason
    global currentlyMissingDevices
    global currentlyAlarmedDevices
    global everTriggeredWithinAlarmCycle
    global alarmedDevicesInCurrentArmCycle
    global missingDevicesInCurrentArmCycle
    global currentAlarmProfile

    now = getTimeSec()

    #for some messages - handle special cases intended for this unit from arduino, and return; if not, drop down to handle general case logic block
    if (msg[0]==homeBaseId and msg[1]==homeBaseId and msg[2]==0xEE and lastArmedTogglePressed < now): #0xEE - arm toggle pressed
        toggleArmed(now, "ARDUINO")
        return

    #alarm message coming in from a device that isn't in the currentlyAlarmedDevices list
    if ((msg[1]==homeBaseId or msg[1]==broadcastId) and msg[2]==0xAA and hex(msg[0]) not in currentlyAlarmedDevices) :
        currentlyAlarmedDevices[hex(msg[0])] = now;
        if (armed and (not "sensorsThatTriggerAlarm" in alarmProfiles[currentAlarmProfile] or ("sensorsThatTriggerAlarm" in alarmProfiles[currentAlarmProfile] and hex(msg[0]) in alarmProfiles[currentAlarmProfile]["sensorsThatTriggerAlarm"]))): 
            print(f">>>>>>>>>>>>>>>>>RECEIVED ALARM SIGNAL FROM {hex(msg[0])} AT {getReadableTime()}<<<<<<<<<<<<<<<<<<")
            alarmed = True
            lastAlarmTime = now;
            alarmedDevicesInCurrentArmCycle[hex(msg[0])] = now;
            everTriggeredWithinAlarmCycle[hex(msg[0])] = now;
            updateCurrentlyTriggeredDevices();
            addEvent({"event": "ALARM", "trigger": alarmReason, "time": getReadableTimeFromTimestamp(lastAlarmTime)})
            print (f">>>>>currentAlarmProfile {currentAlarmProfile}")
            sendMessage([homeBaseId, 0xFF, 0xA0, msg[0]]) #send to the home base's arduino a non-forwardable message with the ID of the alarm-generating device to be added to the list

    #a no-alarm message is coming in from a device that is in the alarmed device list
    elif ((msg[1]==homeBaseId or msg[1]==broadcastId) and msg[2]==0x00 and hex(msg[0]) in currentlyAlarmedDevices):
        print(f"DEVICE {hex(msg[0])} NO LONGER IN currentlyAlarmedDevices - MESSAGE TO REMOVE FROM OLED")
        #home base's arduino should not show this device's ID as one that is currently alarmed
        currentlyAlarmedDevices.pop(hex(msg[0]))
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
        alarmReason += ("" if not alarmReason else " ") +"tripped " + alarmedId
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
    global currentlyAlarmedDevices
    global everTriggeredWithinAlarmCycle
    global memberDevices
    global lastArmedTogglePressed
    global strAlarmedStatus
    global alarmedDevicesInCurrentArmCycle
    global missingDevicesInCurrentArmCycle
    global currentAlarmProfile
    global alarmProfiles
    global garageDoorOpenerId
    global everMissingDevices


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
    outgoingMessage += '"memberDevicesReadable": ' + str(getFriendlyNamesFromDeviceDict(list(memberDevices.keys()))).replace("'","\"")
    outgoingMessage += '}'
    return outgoingMessage


def getPasEventsJsonString():
    global pastEvents

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


def run(webserver_message_queue, alarm_message_queue):
    global debug
    global LISTEN_PORT
    global ser
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
            if (message == "ENABLE-ALARM" and getArmedStatus() == False) :
                toggleArmed(getTimeSec(), "WEB API")
            elif (message == "DISABLE-ALARM" and getArmedStatus() == True) :
                toggleArmed(getTimeSec(), "WEB API")
            elif (message == "ALARM-STATUS") :
                alarm_message_queue.put(getStatusJsonString())
            elif (message == "PAST-EVENTS") :
                alarm_message_queue.put(getPasEventsJsonString())
            elif (message.startswith("SET-ALARM-PROFILE-")):
                profileNumber = int(message.split("SET-ALARM-PROFILE-",1)[1])
                setCurrentAlarmProfile(profileNumber)
            elif (message == "GET-ALARM-PROFILES") :
                alarm_message_queue.put(getProfilesJsonString())
            elif (message == "FORCE-ALARM-SOUND-ON") :
                sendAlarmMessage(True, True)
                time.sleep(.15)
                sendAlarmMessage(False, False)
            elif (message == "TOGGLE-GARAGE-DOOR-STATE") :
                sendMessage([homeBaseId, garageDoorOpenerId, 0x0D, 0x00])
            elif (message == "CLEAR-OLD-DATA") :
                clearOldData()
            elif (message == "ALERT-CHECK-PHONES") :
                currentlyAlarmedDevices[hex(0x17)] = firstTurnedOnTimestamp;
                sendAlarmMessage(True, True)
                time.sleep(.1)
                currentlyAlarmedDevices.pop(hex(0x17))
                sendAlarmMessage(False, False)


        if (not line): continue #nothing on CAN -> repeat while loop (since web server message is already taken care of above)
        
        ser.flushInput()

        if (firstPowerCommandNeedsToBeSent and getTimeSec() > firstTurnedOnTimestamp + timeAllottedToBuildOutMembersSec):
            firstPowerCommandNeedsToBeSent = False
            print(f"Members array built at {getReadableTimeFromTimestamp(getTimeSec())} as:")
            for member in memberDevices:
                print(f"{member} : {memberDevices[member]}")
            print("\n\n\n")
            sendPowerCommandDependingOnArmedState()
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
                    addEvent({"event": "ALARM", "trigger": alarmReason, "time": getReadableTimeFromTimestamp(lastAlarmTime)})
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
    global memberDevices
    global alarmedDevicesInCurrentArmCycle
    global missingDevicesInCurrentArmCycle
    global everMissingDevices
    global currentlyMissingDevices

    everTriggeredWithinAlarmCycle = {}
    alarmedDevicesInCurrentArmCycle = {}
    missingDevicesInCurrentArmCycle = {}
    everMissingDevices = {}
    currentlyMissingDevices = []
    resetMemberDevices()

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
    run(None, None)  # For testing in standalone mode

