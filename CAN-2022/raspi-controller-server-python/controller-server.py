import serial
from datetime import datetime, timezone, timedelta
import math
import numpy as np
import time
import atexit
import tornado.ioloop
import tornado.web

#from pytz import timezone

LISTEN_PORT=8080
ser = serial.Serial('/dev/ttyUSB0', baudrate=115200, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
memberDevices = {}
homeBaseId = 0x14
pastEvents = []
alarmed = False
lastAlarmTime = 0
armed = False #initial condition
lastArmedTogglePressed = 0
alarmTimeLengthSec = 5 #audible and visual alarm will be this long
deviceAbsenceThresholdSec = 2
firstPowerCommandNeedsToBeSent = True
timeAllottedToBuildOutMembersSec = 2
initWaitSeconds = 5

#0x77 - garage, industrial
#0x75 - inside, home
#0x14 - home base
#0x10 - fire alarm bell
#0x15 - siren alarm

#serial message format: 
#   {sender id hex}-{receiver id hex}-{message hex}-{devicetype hex}\n

np.set_printoptions(formatter={'int':hex})






def toggleAlarm(now):
    global lastArmedTogglePressed
    global alarmed
    global armed
    global memberDevices
    
    lastArmedTogglePressed = now
    if (armed == True):
        print(f">>>>>>>>TURNING OFF ALARM AT {getReadableTimeFromTimestamp(now)}<<<<<<<<<")
        pastEvents.append({"event": "DISARMED", "time": getReadableTimeFromTimestamp(now)})
        armed = False #TODO: add logging of event and source
        alarmed = False #reset alarmed state
    else:
        print(f">>>>>>>>TURNING ON ALARM AT {getReadableTimeFromTimestamp(now)}<<<<<<<<<")
        pastEvents.append({"event": "ARMED", "time": getReadableTimeFromTimestamp(now)})
        armed = True #TODO: add logging of event and source
        alarmed = False #reset alarmed state
    
    sendPowerCommandDependingOnArmedState() #TODO - here?
    sendArmedLedSignal() #TODO - here?
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
    printableArr.append(getTime())
    #print("SENDING ", np.array(printableArr)); #TODO: uncomment
    return (hex(message[0]) + "-" + hex(message[1]) + "-" + hex(message[2]) + "-" + hex(message[3]) + "\n")

def sendMessage(messageArray): 
    outgoing = encodeLine(messageArray)
    ser.write(bytearray(outgoing, 'ascii'))
    ser.flushOutput()
    
def getTime():
    return math.floor(datetime.now().timestamp())
    #return math.floor(datetime.now(timezone('US/Pacific')).timestamp())

def getReadableTimeFromTimestamp(timestamp):
    return f"{datetime.fromtimestamp(timestamp).strftime('%c')} LOCAL TIME"

def possiblyAddMember(msg):
    global memberDevices
    now = getTime()
    if (msg[0] != homeBaseId):
        if (msg[0] not in memberDevices) :
            print(f"Adding new device to members list {hex(msg[0])} at {getReadableTimeFromTimestamp(now)}")
            memberDevices[msg[0]] = {'firstSeen': now, 'deviceType': msg[3], 'lastSeen': now}
        else :
            memberDevices[msg[0]]['lastSeen'] = now

def checkMembersOnline():
    now = getTime()
    missingMembers = []
    for memberId in memberDevices :
        if (memberDevices[memberId]['lastSeen'] + deviceAbsenceThresholdSec < now) :
            print(f"Adding missing device {hex(memberId)} at {getReadableTimeFromTimestamp(now)}")
            missingMembers.append(memberId)
    return missingMembers

def sendArmedLedSignal():
    global armed
    if (armed == True):
        messageToSend = [homeBaseId, 0x00, 0xD1, 0x01]
        print(f">>>> SENDING LED ON SIGNAL {np.array(messageToSend)}")
    else:
        messageToSend = [homeBaseId, 0x00, 0xD0, 0x01]
        print(f">>>> SENDING LED OFF SIGNAL {np.array(messageToSend)}")
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
            messageToSend = [homeBaseId, member, 0x0F, 0x01]
            sendMessage(messageToSend) #stand up power - 0x0F enabled / 0x01 disabled
            print(f">>>> SENDING POWER ON SIGNAL {np.array(messageToSend)}")
            time.sleep(15/100) #15 msec sleep

def exitSteps():
    global pastEvents
    global homeBaseId
    print(f"\n\nEXITING AT {getReadableTimeFromTimestamp(getTime())}")
    print("BROADCASTING QUIET-ALL-ALARMS SIGNAL")
    sendMessage([homeBaseId, 0x00, 0xCC, 0x01]) #reset all devices (broadcast)
    print("BROADCASTING ALL-SENSOR-DEVICES-OFF SIGNAL")
    sendMessage([homeBaseId, 0x00, 0x01, 0x01]) #all devices off (broadcast)
    print("\nPAST EVENTS LIST FOLLOWS:")
    for line in pastEvents:
        print(f"\t{line}")    

def handleMessage(msg):
    possiblyAddMember(msg)
    missingDevices = checkMembersOnline()
    global alarmed
    global pastEvents
    global homeBaseId
    global lastAlarmTime
    global armed
    global lastArmedTogglePressed
    global memberDevices
    now = getTime();

    #for some messages - handle special cases intended for this unit from arduino, and return; if not, drop down to handle general case logic block
    if (msg[0]==homeBaseId and msg[1]==homeBaseId and msg[2]==0xEE and lastArmedTogglePressed < now): #0xEE - arm toggle pressed
        toggleAlarm(now)
        return

    #handle general case
    if (alarmed == False) :
        if (msg[1]==homeBaseId and msg[2]==0xAA): 
            print(f">>>>>>>>>>>>>>>>>RECEIVED ALARM SIGNAL FROM {hex(msg[0])} AT {getReadableTimeFromTimestamp(now)}<<<<<<<<<<<<<<<<<<")
            alarmed = True
            lastAlarmTime = now
            alarmReason = f"tripped {hex(msg[0])}"
            pastEvents.append({"event": "ALARM", "trigger": alarmReason, "time": getReadableTimeFromTimestamp(lastAlarmTime)})
        elif (len(missingDevices) > 0):
            print(f">>>>>>>>>>>>>>>>>>>>FOUND missing devices {missingDevices}<<<<<<<<<<<<<<<<<<<")
            alarmed = True
            lastAlarmTime = now
            alarmReason = f"missing device(s) {missingDevices}"
            pastEvents.append({"event": "ALARM", "trigger": alarmReason, "time": getReadableTimeFromTimestamp(lastAlarmTime)})
        
    elif (alarmed and lastAlarmTime + alarmTimeLengthSec < now and len(missingDevices) == 0 and (msg[1]==homeBaseId and msg[2]==0x00)):
        alarmed = False #TODO: for now - after 3000ms after first alarm message, the alarm is turned off, given ANY device sending a non-alarmed code. This approach is fundamentally fucked, but temporary.

    if (armed and alarmed):
        messageToSend = [homeBaseId, 0x00, 0xBB, 0x01] #TODO: send to those nodes that need to be triggered
    else:
        messageToSend = [homeBaseId, 0x00, 0xCC, 0x01] #TODO: send to those nodes that need to be reset
    sendMessage(messageToSend)

atexit.register(exitSteps)
print(f"STARTING ALARM SCRIPT AT {getReadableTimeFromTimestamp(getTime())}.\nWAITING {initWaitSeconds} SECONDS TO SET UP SERIAL BUS...")
time.sleep(initWaitSeconds)
print(f"DONE WAITING, OPERATIONAL NOW AT {getReadableTimeFromTimestamp(getTime())}. STATUS:\nARMED: {armed}\nALARMED: {alarmed}\n\n\n")

ser.flushOutput()
ser.flushInput()
sendMessage([homeBaseId, 0x00, 0xCC, 0x01]) #reset all devices (broadcast)
sendArmedLedSignal()
firstTurnedOnTimestamp = getTime()


#--------------------------SERVER-----------------------------
# class StatusHandler(tornado.web.RequestHandler):
#     def get(self):
#         self.write(f"{armed}")

# class Mode0Handler(tornado.web.RequestHandler):
#     def get(self):
#         global armed
#         if (armed == True):
#             toggleAlarm(getTime())
#         self.write(f"{armed}")

# class Mode1Handler(tornado.web.RequestHandler):
#     def get(self):
#         global armed
#         if (armed == False):
#             toggleAlarm(getTime())
#         self.write(f"{armed}")
        
# class ListEventsHandler(tornado.web.RequestHandler):
#     def get(self):
#         for line in pastEvents:
#              self.write(f"\t{line}<br>") 

# class MainHandler(tornado.web.RequestHandler):
#     def get(self):
#         global armed

# def make_app():
#     return tornado.web.Application([
#         (r"/status", StatusHandler),
#         (r"/mode0", Mode0Handler),
#         (r"/mode1", Mode1Handler),
#         (r"/events", ListEventsHandler)
#     ])

# if __name__ == "__main__":
#     app = make_app()
#     app.listen(LISTEN_PORT)
#     tornado.ioloop.IOLoop.current().start()
#----------------------//////SERVER-----------------------------



for line in ser:
    ser.flushInput()

    if (firstPowerCommandNeedsToBeSent and getTime() > firstTurnedOnTimestamp + timeAllottedToBuildOutMembersSec):
        firstPowerCommandNeedsToBeSent = False
        print(f"Members array built at {getReadableTimeFromTimestamp(getTime())} as:")
        for member in memberDevices:
            print(f"{hex(member)} : {memberDevices[member]}")
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
    msg.append(getTime())
    #print("GETTING", np.array(msg)) #TODO: uncomment

    handleMessage(msg)

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


