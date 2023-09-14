import serial
from datetime import datetime, timezone, timedelta
import math
import numpy as np
import time
import atexit
import tornado.ioloop
import tornado.web
import json

debug = False
LISTEN_PORT=8080
ser = serial.Serial('/dev/ttyUSB0', baudrate=115200, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=.25) #quarter second timeout so that Serial.readLine() doesn't block if no message(s) on CAN
print("Arduino: serial connection with PI established")
memberDevices = {} #map of {string hex id:{properties}}
deviceDictionary = {
    "0x80": "garage motion sensor 0x80",
    "0x75": "inside motion sensor 0x75",
    "0x30": "garage car door sensor 0x30",
    "0x31": "garage side door sensor 0x31",
    "0x14": "home base",
    "0xFF": "home base communicating to its arduino",
    "0x10": "fire alarm bell 0x10",
    "0x15": "piezo 120db alarm 0x15",
    "0x99": "indoor buzzer with led 0x99"
}
alarmProfiles = [{
    "name": "Default (all->all)" #all missing and all triggers BROADCAST ALARM
}, {
    "name": "Night",
    "sensorsThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30"],
    "missingDevicesThatTriggerAlarm": ["0x80", "0x75", "0x31", "0x30"],
    "alarmOutputDevices": ["0x99"]
}]
lastSentMessageTimeMsec = 0
homeBaseId = 0x14 #interdependent with deviceDictionary
broadcastId = 0x00
pastEvents = []
alarmed = False
alarmedDevicesInCurrentArmCycle = {}
missingDevicesInCurrentArmCycle = {}
alarmedDevices = {} #map of {string hex id:int alarmTimeSec}
currentlyAlarmedDevices = {} #map of {string hex id:int alarmTimeSec}
missingDevices = []
lastAlarmTime = 0
armed = False #initial condition
lastArmedTogglePressed = 0
alarmTimeLengthSec = 5 #audible and visual alarm will be this long; set to negative if want this to persist until manually canceled; set to 0 to be as long as the alarm signal is coming in from sensor(s)
deviceAbsenceThresholdSec = 7
firstPowerCommandNeedsToBeSent = True
timeAllottedToBuildOutMembersSec = 2
initWaitSeconds = 5
alarmReason = ""
sendTimeoutMsec = 500
lastCheckedMissingDevicesMsec = 0
checkForMissingDevicesEveryMsec = 750
currentAlarmProfile = 0 # 0 = default

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
    global alarmedDevices
    global alarmedDevicesInCurrentArmCycle
    global missingDevicesInCurrentArmCycle
    
    lastArmedTogglePressed = now
    if (armed == True):
        print(f">>>>>>>>TURNING OFF ALARM AT {getReadableTimeFromTimestamp(now)} PER {method}<<<<<<<<<")
        addEvent({"event": "DISARMED", "time": getReadableTimeFromTimestamp(now), "method": method})
        armed = False #TODO: add logging of event and source
        alarmed = False #reset alarmed state
        alarmedDevices = {}
        alarmedDevicesInCurrentArmCycle = {}
        missingDevicesInCurrentArmCycle = {}
    else:
        print(f">>>>>>>>TURNING ON ALARM AT {getReadableTimeFromTimestamp(now)} PER {method}<<<<<<<<<")
        addEvent({"event": "ARMED", "time": getReadableTimeFromTimestamp(now), "method": method})
        armed = True #TODO: add logging of event and source
        alarmed = False #reset alarmed state
        alarmedDevices = {}
    
    
    sendPowerCommandDependingOnArmedState() 
    sendArmedLedSignal() 
    print("Clearing member devices list")
    memberDevices = {} #reset all members on the bus when turning on/off


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
    outgoing = encodeLine(messageArray)
    ser.write(bytearray(outgoing, 'ascii'))
    ser.flushOutput()
    lastSentMessageTimeMsec = getTimeMsec()


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
    lastCheckedMissingDevicesMsec = getTimeMsec()
    missingMembers = []
    for memberId in memberDevices :
        if (memberDevices[memberId]['lastSeen'] + deviceAbsenceThresholdSec < now) :
            print(f"Adding missing device {memberId} at {getReadableTime()}. missing for {(getTimeSec()-memberDevices[memberId]['lastSeen'])} seconds")
            missingMembers.append(memberId)
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
    global missingDevices
    global alarmTimeLengthSec
    global currentlyAlarmedDevices
    global alarmedDevices
    global alarmedDevicesInCurrentArmCycle
    global missingDevicesInCurrentArmCycle
    global currentAlarmProfile

    now = getTimeSec()

    #for some messages - handle special cases intended for this unit from arduino, and return; if not, drop down to handle general case logic block
    if (msg[0]==homeBaseId and msg[1]==homeBaseId and msg[2]==0xEE and lastArmedTogglePressed < now): #0xEE - arm toggle pressed
        toggleArmed(now, "ARDUINO")
        return

    #alarm message coming in from a device that isn't in the currentlyAlarmedDevices list
    if (armed and (msg[1]==homeBaseId or msg[1]==broadcastId) and msg[2]==0xAA and hex(msg[0]) not in currentlyAlarmedDevices and (currentAlarmProfile == 0 or (currentAlarmProfile > 0 and hex(msg[0]) in alarmProfiles[currentAlarmProfile]["sensorsThatTriggerAlarm"]))): 
        print(f">>>>>>>>>>>>>>>>>RECEIVED ALARM SIGNAL FROM {hex(msg[0])} AT {getReadableTime()}<<<<<<<<<<<<<<<<<<")
        alarmed = True
        lastAlarmTime = now;
        currentlyAlarmedDevices[hex(msg[0])] = now;
        alarmedDevicesInCurrentArmCycle[hex(msg[0])] = now;
        alarmedDevices[hex(msg[0])] = now;
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
    global missingDevices

    alarmReason = ""
    for missingId in missingDevices:
        alarmReason += ("" if not alarmReason else " ") + "missing " + missingId
    for alarmedId in currentlyAlarmedDevices:
        alarmReason += ("" if not alarmReason else " ") +"tripped " + alarmedId
    if (debug): print("Updated alarm reason to: " + alarmReason)


def getProfilesJsonString():
    global currentAlarmProfile
    global alarmProfiles

    profilesJSON = ""
    for profile in alarmProfiles:
        profilesJSON += json.dumps(profile) + ","
    profilesJSON = profilesJSON[:-1]

    strReturn = '{"profiles": [' + profilesJSON + ']}'
    return strReturn


def getStatusJsonString():
    global currentlyAlarmedDevices
    global alarmedDevices
    global memberDevices
    global lastArmedTogglePressed
    global strAlarmedStatus
    global alarmedDevicesInCurrentArmCycle
    global missingDevicesInCurrentArmCycle
    global currentAlarmProfile
    global alarmProfiles

    strAlarmedStatus = "ALARM" if alarmed else "NORMAL"
    outgoingMessage = '{"armStatus": "' + ("ARMED" if armed else "DISARMED") + '",'
    outgoingMessage += '"alarmStatus": "' + strAlarmedStatus + '",'
    outgoingMessage += '"profile": "' + alarmProfiles[currentAlarmProfile]["name"] + '",'
    outgoingMessage += '"profileNumber": "' + str(currentAlarmProfile) + '",'
    outgoingMessage += '"currentTriggeredDevices": ' + str(list(currentlyAlarmedDevices.keys())).replace("'","\"") + ","
    outgoingMessage += '"currentMissingDevices": ' + str(missingDevices).replace("'","\"") + ','
    outgoingMessage += '"everTriggeredWithinAlarmCycle": ' + str(list(alarmedDevices.keys())).replace("'","\"") + ","
    outgoingMessage += '"everTriggeredWithinArmCycle": ' + str(list(alarmedDevicesInCurrentArmCycle.keys())).replace("'","\"") + ","
    outgoingMessage += '"everMissingWithinArmCycle": ' + str(list(missingDevicesInCurrentArmCycle.keys())).replace("'","\"") + ","
    outgoingMessage += '"memberCount": ' + str(len(memberDevices)) + ','
    outgoingMessage += '"memberCount": ' + str(len(memberDevices)) + ','
    outgoingMessage += '"memberDevices": ' + str(list(memberDevices.keys())).replace("'","\"") + ','
    outgoingMessage += '"memberDevicesReadable": ' + str(getFriendlyNamesFromDeviceDict(list(memberDevices.keys()))).replace("'","\"")
    #outgoingMessage += '"memberDetails": ' + str(memberDevices).replace("'","\"")
    outgoingMessage += '}'
    return outgoingMessage


def getPasEventsJsonString():
    global pastEvents

    outgoingMessage = '{"pastEvents": ' + str(pastEvents).replace("'","\"")
    outgoingMessage += '}'
    return outgoingMessage


def run(webserver_message_queue, alarm_message_queue):
    global debug
    global LISTEN_PORT
    global ser
    global memberDevices
    global currentlyAlarmedDevices
    global alarmedDevices
    global homeBaseId
    global pastEvents
    global alarmed
    global lastAlarmTime
    global armed
    global lastArmedTogglePressed
    global alarmTimeLengthSec
    global deviceAbsenceThresholdSec
    global firstPowerCommandNeedsToBeSent
    global timeAllottedToBuildOutMembersSec
    global initWaitSeconds
    global lastSentMessageTimeMsec
    global sendTimeoutMsec
    global missingDevices
    global checkForMissingDevicesEveryMsec
    global lastCheckedMissingDevicesMsec
    global alarmProfiles
    global currentAlarmProfile

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
                print("SETTING ALARM PROFILE " + str(message.split("SET-ALARM-PROFILE-",1)[1]))
                setCurrentAlarmProfile(int(message.split("SET-ALARM-PROFILE-",1)[1]))
            elif (message == "GET-ALARM-PROFILES") :
                 alarm_message_queue.put(getProfilesJsonString())

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


        if (lastCheckedMissingDevicesMsec+checkForMissingDevicesEveryMsec < getTimeMsec()):
            if (debug): 
                print(f">>>Checking for missing devices at {getTimeMsec()}")
            missingDevices = checkMembersOnline()

            if (armed and len(missingDevices) > 0):
                updateCurrentlyTriggeredDevices()
                print(f">>>>>>>>>>>>>>>>>>>> ADDING MISSING DEVICES {arrayToString(missingDevices)} at {getReadableTime()}<<<<<<<<<<<<<<<<<<<")
                alarmed = True
                lastAlarmTime = getTimeSec()
                addEvent({"event": "ALARM", "trigger": alarmReason, "time": getReadableTimeFromTimestamp(lastAlarmTime)})

        #if currently alarmed and there are no missing or alarmed devices and it's been long enough that alarmTimeLengthSec has run out, DISABLE ALARM FLAG
        if (alarmed and alarmTimeLengthSec > -1 and lastAlarmTime + alarmTimeLengthSec < getTimeSec() and len(missingDevices) == 0 and len(currentlyAlarmedDevices) == 0):
            alarmed = False
            addEvent({"event": "FINISHED_ALARM", "time": getReadableTimeFromTimestamp(lastAlarmTime)})
            alarmedDevices = {}
            currentlyAlarmedDevices = {}
            updateCurrentlyTriggeredDevices()
            sendMessage([homeBaseId, 0xFF, 0xC0, 0x01]) #TODO: send to those nodes that need to be reset

        elif (alarmed and len(missingDevices) > 0):
            alarmed = True
            updateCurrentlyTriggeredDevices();

        elif (alarmed and len(currentlyAlarmedDevices) > 0):
            alarmed = True
            updateCurrentlyTriggeredDevices();


        #possibly send a message (if it's been sendTimeoutMsec)
        if (getTimeMsec() > (lastSentMessageTimeMsec+sendTimeoutMsec)):
            if (armed and alarmed):
                if (currentAlarmProfile > 0):
                    for deviceToBeAlarmed in alarmProfiles[currentAlarmProfile]["alarmOutputDevices"]:
                        sendMessage([homeBaseId, int(deviceToBeAlarmed, 16), 0xBB, 0x01])
                else:
                    sendMessage([homeBaseId, 0x00, 0xBB, 0x01])
            else:
                alarmed = False
                if (currentAlarmProfile > 0):
                    for deviceToBeAlarmed in alarmProfiles[currentAlarmProfile]["alarmOutputDevices"]:
                        sendMessage([homeBaseId, int(deviceToBeAlarmed, 16), 0xCC, 0x01])
                else:
                    sendMessage([homeBaseId, 0x00, 0xCC, 0x01])
                alarmedDevices = {}
                currentlyAlarmedDevices = {}


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

