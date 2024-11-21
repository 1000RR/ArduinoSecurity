#include <SPI.h>
#include <mcp2515.h>

struct can_frame myCanMessage;
MCP2515 mcp2515(10);
MCP2515::ERROR canMessageError;

struct Device {
  int sensorPin;
  int relayPin; //-1 for no relay
  int sensorVal;
  int myCanId;
  bool effectivelyEnabled; //this is also the relay state for devices with relay, ie relayPin != -1
  int deviceType;
};

const int numDevices = 2; /* num connected devices */

Device devices[numDevices] = {
  {
    sensorPin: 5,
    relayPin: -1, /* -1 = no relay; writing LOW to this turns relay ON */
    sensorVal: 0 /*variable to store the sensor status (value)*/,
    myCanId: 0x66,
    effectivelyEnabled: true, /*false = off; true = on; mirror value: relayState*/
    deviceType: 2
  },
  {
    sensorPin: 7, 
    relayPin: -1, /* -1 = no relay; writing LOW to this turns relay ON */
    sensorVal: 0 /*variable to store the sensor status (value)*/,
    myCanId: 0x67,
    effectivelyEnabled: true, /*false = off; true = on; mirror value: relayState*/
    deviceType: 1
  }
};

const int BROADCAST_ADDR = 0x00;
const int homebaseCanId = 0x14;
struct can_frame incomingCanMsg;
String ERROR_NAMES[] = {"OK", "FAIL", "ALLTXBUSY", "FAILINIT", "FAILTX", "NOMSG"};
long lastSentMillis = 0;
int sendEveryMillis = 1000 / numDevices;


/// MSG FORMAT: [0] TO (1 byte, number = specific ID OR 00 = broadcast)
///             [1] MSG (1 byte)
///             [2] DEVICETYPE (1 byte)
/// SENSOR MESSAGE DICTIONARY (00 - enabled and status ok, AA - enabled and status alarmed, BB - trigger alarm device, CC - reset alarm, FF - disabled)
/// HOME BASE MESSAGE DICTIONARY (0F - enable yourself, O1 - disable yourself)
/// DEVICE TYPE DICTIONARY: (01 controller, 02 pir/microwave alarm, 03 bell, 04 visual alarm, 05 door open sensor)
/// HOME BASE CAN ID = 0x14;

// enum ERROR {
//     ERROR_OK        = 0,
//     ERROR_FAIL      = 1,
//     ERROR_ALLTXBUSY = 2,
//     ERROR_FAILINIT  = 3,
//     ERROR_FAILTX    = 4,
//     ERROR_NOMSG     = 5
// }

void setup()
{
  while (!Serial);
  
  Serial.begin(115200);

  mcp2515.reset();
  mcp2515.setBitrate(CAN_125KBPS);
  mcp2515.setNormalMode();

  //initialize the 
  for (int i = 0; i<numDevices; i++) {
    pinMode(devices[i].sensorPin, INPUT_PULLUP); // initialize sensor as an input
    if (devices[i].relayPin != -1) {
      pinMode(devices[i].relayPin, OUTPUT);
      
      if (devices[i].effectivelyEnabled == true){
        digitalWrite(devices[i].relayPin, LOW); // low = on
      } else {
        digitalWrite(devices[i].relayPin, HIGH); // high = off
      }
    }
  }

  /* set up those parts of the outgoing CAN message that don't change */
  myCanMessage.can_dlc = 3;
  myCanMessage.data[0] = homebaseCanId;
  myCanMessage.data[1] = 0x00;
}

void setDeviceEnableState(int deviceNumber, bool newState)
{
  if (newState == true && devices[deviceNumber].effectivelyEnabled == false)
  {
    devices[deviceNumber].effectivelyEnabled = true;
    if (devices[deviceNumber].relayPin != -1) {
      Serial.println(">>>>>>>>>>>ENABLING RELAY>>>>>>>>>>>");
      digitalWrite(devices[deviceNumber].relayPin, LOW); // low = on
    } else {
      Serial.println(">>>>>>>>>>>ENABLING LOGICAL DEVICE>>>>>>>>>>>");
    }
    
    // delay(100); //delay sending anything while the sensor gets power and begins reading an OK value while powering up
  }
  else if (newState == false && devices[deviceNumber].effectivelyEnabled == true)
  {
    devices[deviceNumber].effectivelyEnabled = false;
    
    if (devices[deviceNumber].relayPin != -1) {
      digitalWrite(devices[deviceNumber].relayPin, HIGH); // high = off
      Serial.println(">>>>>>>>>>>DISABLING RELAY>>>>>>>>>>>");
    } else {
      Serial.println(">>>>>>>>>>>DISABLING LOGICAL DEVICE>>>>>>>>>>>");
    }
  }
}

void makeMessage(int deviceNumber, int message)
{
  myCanMessage.can_id = devices[deviceNumber].myCanId;
  myCanMessage.data[0] = homebaseCanId;
  myCanMessage.data[2] = devices[deviceNumber].deviceType;
  
  if (devices[deviceNumber].effectivelyEnabled == true && devices[deviceNumber].sensorVal == 1) {
    myCanMessage.data[1] = 0xAA; // alarm
  } else if (devices[deviceNumber].effectivelyEnabled == true && devices[deviceNumber].sensorVal == 0) {
    myCanMessage.data[1] = 0x00; // ok
  } else if (devices[deviceNumber].effectivelyEnabled == false) {
    myCanMessage.data[1] = 0xFF;
  }
}

void sendMessage(int deviceNumber, int message)
{
  makeMessage(deviceNumber, message);
  mcp2515.sendMessage(&myCanMessage);

  Serial.print("Message sent to 0x");
  Serial.print(myCanMessage.data[0], HEX);
  Serial.print(" from 0x");
  Serial.print(devices[deviceNumber].myCanId, HEX);
  Serial.print(" message: ");
  Serial.println(myCanMessage.data[1], HEX);
}

bool readIncomingCanMessage()
{
  canMessageError = mcp2515.readMessage(&incomingCanMsg);
  if (canMessageError == MCP2515::ERROR_OK) {
    if (incomingCanMsg.can_id == homebaseCanId) {
      return true;
    }
  }

  return false;
}

/* 
 *  returns -1000 for broadcast,
 *  returns -1 for not matched,
 *  returns id of device in devices array. id is in range [0, numDevices)
 */
int matchMessageToThisDevice()
{
  if (incomingCanMsg.can_id == homebaseCanId) // received message coming from home base
  {
    if (incomingCanMsg.data[0] == BROADCAST_ADDR) //received message has recipient listed as BROADCAST
    {
      return -1000;
    }
    for (int i = 0; i < numDevices; i++) {
      if (incomingCanMsg.data[0] == devices[i].myCanId) { //received message has recipient specified as one of the devices in "devices"
        return i;
      }
    }
  }
  return -1;
}

void processIncomingCanMessage()
{
  int deviceNum = matchMessageToThisDevice();
  bool newState;

  if (incomingCanMsg.data[1] == 0x0F)
  { // enable
    newState = true;
  }
  else if (incomingCanMsg.data[1] == 0x01)
  { // disable
    newState = false;
  }
  
  if (deviceNum > -1) { //specific device
    setDeviceEnableState(deviceNum, newState);
  } else if (deviceNum == -1000) { //should affect all connected devices
    for (int i = 0; i < numDevices; i++) {
      setDeviceEnableState(deviceNum, newState);
    }
  } else {
    Serial.println("INCOMING CAN MESSAGE NOT ATTRIBUTED TO THIS DEVICE");
  }
}

void loop() /* go through all devices: read incoming CAN message, send message for each device when appropriate */
{
  int loopDeviceIndex = 0;

  if (readIncomingCanMessage())
  {
    Serial.println(">>>>>>>READMESSAGE TRUE");
    Serial.print(">>>>>>>MESSAGE: ");
    debugPrintIncoming();
    processIncomingCanMessage();
  }

  for (int i = 0; i < numDevices; i++) {
    devices[i].sensorVal = digitalRead(devices[i].sensorPin); /*LOW by default, no motion detected*/
  }
  
  long now = millis();
  if ((now > lastSentMillis + sendEveryMillis) || now < lastSentMillis)
  { // only send a message if it's been "sendEveryMillis" OR the timer has cycled around LONG
    sendMessage(loopDeviceIndex,0);
    lastSentMillis = now;
  }
}

void debugPrintIncoming()
{
  String output = "\n\n>>>INCOMING MESSAGE\nSENDER CAN ID: " + String(incomingCanMsg.can_id, HEX) + " LENGTH: " + String(incomingCanMsg.can_dlc, HEX) + "\n";
  for (int i = 0; i < incomingCanMsg.can_dlc; i++)
  { // print the data
    output = output + " byte " + i + ": " + String(incomingCanMsg.data[i], HEX);
  }
  output += "\n";
  Serial.println(output);
}
