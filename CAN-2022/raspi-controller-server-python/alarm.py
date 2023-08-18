import serial
from datetime import datetime, timezone, timedelta
import math
import numpy as np
import time
import atexit
import tornado.ioloop
import tornado.web
import json

debug = True
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
    "0x10": "fire alarm bell",
    "0x15": "piezo 120db alarm 0x15",
    "0x99": "indoor siren with led"
}
lastSentMessageTimeMsec = 0
homeBaseId = 0x14 #interdependent with deviceDictionary
broadcastId = 0x00
pastEvents = []
alarmed = False
alarmedDevices = {} #map of {string hex id:int alarmTimeSec}
missingDevices = []
lastAlarmTime = 0
armed = False #initial condition
lastArmedTogglePressed = 0
alarmTimeLengthSec = 5 #audible and visual alarm will be this long
deviceAbsenceThresholdSec = 5
firstPowerCommandNeedsToBeSent = True
timeAllottedToBuildOutMembersSec = 2
initWaitSeconds = 5
alarmReason = ""
sendTimeoutMsec = 500
lastCheckedMissingDevicesMsec = 0
checkForMissingDevicesEveryMsec = 750

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

np.set_printoptions(formatter={'int':hex})

def addEvent(event):
    global pastEvents
    pastEvents.append(event)


def getArmedStatus():
    global armed
    return armed


def toggleAlarm(now, method):
    global lastArmedTogglePressed
    global alarmed
    global armed
    global memberDevices
    global deviceDictionary
    
    lastArmedTogglePressed = now
    if (armed == True):
        print(f">>>>>>>>TURNING OFF ALARM AT {getReadableTimeFromTimestamp(now)} PER {method}<<<<<<<<<")
        addEvent({"event": "DISARMED", "time": getReadableTimeFromTimestamp(now), "method": method})
        armed = False #TODO: add logging of event and source
        alarmed = False #reset alarmed state
    else:
        print(f">>>>>>>>TURNING ON ALARM AT {getReadableTimeFromTimestamp(now)} PER {method}<<<<<<<<<")
        addEvent({"event": "ARMED", "time": getReadableTimeFromTimestamp(now), "method": method})
        armed = True #TODO: add logging of event and source
        alarmed = False #reset alarmed state
    
    
    sendPowerCommandDependingOnArmedState() #TODO - here?
    sendArmedLedSignal() #TODO - here?
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


def checkMembersOnline():
    now = getTimeSec()
    global lastCheckedMissingDevicesMsec
    lastCheckedMissingDevicesMsec = getTimeMsec()
    missingMembers = []
    for memberId in memberDevices :
        if (memberDevices[memberId]['lastSeen'] + deviceAbsenceThresholdSec < now) :
            print(f"Adding missing device {memberId} at {getReadableTime()}. missing for {(getTimeSec()-memberDevices[memberId]['lastSeen'])} seconds")
            missingMembers.append(memberId)
        ##TODO WRITE A FOUND MISSING DEVICE HANDLER THAT OUTPUTS TO LOG
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
    global alarmedDevices
    now = getTimeSec()

    #for some messages - handle special cases intended for this unit from arduino, and return; if not, drop down to handle general case logic block
    if (msg[0]==homeBaseId and msg[1]==homeBaseId and msg[2]==0xEE and lastArmedTogglePressed < now): #0xEE - arm toggle pressed
        toggleAlarm(now, "ARDUINO")
        return

    #alarm message coming in from a device that isn't in the alarmedDevices list
    if ((msg[1]==homeBaseId or msg[1]==broadcastId) and msg[2]==0xAA and hex(msg[0]) not in alarmedDevices): 
        print(f">>>>>>>>>>>>>>>>>RECEIVED ALARM SIGNAL FROM {hex(msg[0])} AT {getReadableTime()}<<<<<<<<<<<<<<<<<<")
        alarmed = True
        lastAlarmTime = now;
        alarmedDevices[hex(msg[0])] = now;
        updateAlarmReason();
        addEvent({"event": "ALARM", "trigger": alarmReason, "time": getReadableTimeFromTimestamp(lastAlarmTime)})
        
        if (armed):
            sendMessage([homeBaseId, 0xFF, 0xA0, msg[0]]) #send to the home base's arduino a non-forwardable message with the ID of the alarm-generating device to be added to the list

    #a no-alarm message is coming in from a device that is in the alarmed device list
    elif ((msg[1]==homeBaseId or msg[1]==broadcastId) and msg[2]==0x00 and hex(msg[0]) in alarmedDevices):
        print(f"DEVICE {hex(msg[0])} NO LONGER IN ALARMEDDEVICES - MESSAGE TO REMOVE FROM OLED")
        #home base's arduino should not show this device's ID as one that is currently alarmed
        alarmedDevices.pop(hex(msg[0]))
        updateAlarmReason();
        sendMessage([homeBaseId, 0xFF, 0xB0, msg[0]]) 
        

        
def updateAlarmReason():
    global alarmReason
    alarmReason = ""
    for missingId in missingDevices:
        alarmReason += ("" if not alarmReason else " ") + "missing " + missingId
    for alarmedId in alarmedDevices:
        alarmReason += ("" if not alarmReason else " ") +"tripped " + alarmedId
    print("Updated alarm reason to: " + alarmReason)

def getStatusJsonString():
    strAlarmedStatus = "ALARM " + alarmReason if alarmed else "NORMAL"
    outgoingMessage = '{"armStatus": "' + ("ARMED" if armed else "DISARMED") + '",'
    outgoingMessage += ('"alarmStatus": "' + strAlarmedStatus + '",') if armed else ""
    outgoingMessage += '"memberCount": ' + str(len(memberDevices)) + ','
    outgoingMessage += '"memberDevices": ' + str(list(memberDevices.values())).replace("(","{").replace(")","}").replace("'","\"")
    outgoingMessage += '}'
    return outgoingMessage


def run(webserver_message_queue, alarm_message_queue):
    global debug
    global LISTEN_PORT
    global ser
    global memberDevices
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
                toggleAlarm(getTimeSec(), "WEB API")
            elif (message == "DISABLE-ALARM" and getArmedStatus() == True) :
                toggleAlarm(getTimeSec(), "WEB API")
            elif (message == "ALARM-STATUS") :
                alarm_message_queue.put(getStatusJsonString())

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

            if (len(missingDevices) > 0):
                print(f">>>>>>>>>>>>>>>>>>>> ADDING MISSING DEVICES {arrayToString(missingDevices)} at {getReadableTime()}<<<<<<<<<<<<<<<<<<<")
                alarmed = True
                lastAlarmTime = getTimeSec()
                updateAlarmReason()
                #TODO: show missing devices on oled?
                addEvent({"event": "ALARM", "trigger": alarmReason, "time": getReadableTimeFromTimestamp(lastAlarmTime)})

        #if currently alarmed and there are no missing or alarmed devices and it's been long enough that alarmTimeLengthSec has run out, DISABLE ALARM FLAG
        if (alarmed and lastAlarmTime + alarmTimeLengthSec < getTimeSec() and len(missingDevices) == 0 and len(alarmedDevices) == 0):
            alarmed = False
            updateAlarmReason()
            sendMessage([homeBaseId, 0xFF, 0xC0, 0x01]) #TODO: send to those nodes that need to be reset

        #possibly send a message (if it's been sendTimeoutMsec)
        if (getTimeMsec() > (lastSentMessageTimeMsec+sendTimeoutMsec)):
            if (armed and alarmed):
                sendMessage([homeBaseId, 0x00, 0xBB, 0x01]) #TODO: send to those nodes that need to be triggered
            else:
                sendMessage([homeBaseId, 0x00, 0xCC, 0x01]) #TODO: send to those nodes that need to be reset

#TODO:
#This should be in the polling thread
#Other thread should have a web server that is behind good auth, APIs should control things.
#DONE Other thread should take care of tracking what devices are present, and alarming if any disappear
#Other thread should have configurable profiles of which devices: are on, should be listened to, what the outcome is when tripped
#DONE Other thread should be able to switch between armed and disarmed
#Other thread should be able to switch current profile
#DONE Other thread should allow for genie remote on/off operation
#DONE Other thread should log first land last occurrence of presence of a device
#Other thread should log REASON for alarm (alarm, absence of device for X, policy at the time, and time)
#DONE Other thread should enable high current-drawing alarm devices in a staged way with a delay- THE SECOND DIGIT OF THE DEVICE TYPE SHOULD BE (0 - low current draw; 1 - high current draw)


#pmd.reset_output_buffer()


if __name__ == "__main__":
    run(None, None)  # For testing in standalone mode

