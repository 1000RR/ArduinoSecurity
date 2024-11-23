#include <SPI.h>
#include <mcp2515.h>

int loopDeviceIndex = 0;

bool enableBuzzer = true;
bool buzzerSounding = false;
int buzzerPin = 3;                //d3=3 has pwm
long previousMillis = 0; // Tracks the last tone update
long toneInterval = 50;  // Interval between frequency changes (ms)
int frequency = 500;              // Current frequency
bool increasing = true;           // Direction of frequency sweep

struct can_frame myCanMessage;
MCP2515 mcp2515(10);
MCP2515::ERROR canMessageError;

struct Device {
  int sensorPin; //sensor pin is connected to ground via resistor for a LOW signal (alarm at rest) or chain broken for a HIGH signal (alarm triggered)
  int relayPin; //-1 for no relay
  int sensorVal;
  int myCanId;
  bool effectivelyEnabled; //this is also the relay state for devices with relay, ie relayPin != -1
  int deviceType;
};

const int numDevices = 3; /* num connected devices */

Device devices[numDevices] = { /*don't enable too many/any devices that draw current, like PIRs - the initial current draw will be too great*/
  {
    sensorPin: 5,
    relayPin: -1, /* -1 = no relay; writing LOW to this turns relay ON */
    sensorVal: 0 /*variable to store the sensor status (value)*/,
    myCanId: 0x66,
    effectivelyEnabled: true, /*false = off; true = on; mirror value: relayState*/
    deviceType: 5
  },
  {
    sensorPin: 7, 
    relayPin: -1, /* -1 = no relay; writing LOW to this turns relay ON */
    sensorVal: 0 /*variable to store the sensor status (value)*/,
    myCanId: 0x67,
    effectivelyEnabled: true, /*false = off; true = on; mirror value: relayState*/
    deviceType: 5
  },
  {
    sensorPin: 9, 
    relayPin: 6, /* -1 = no relay; writing LOW to this turns relay ON */
    sensorVal: 0 /*variable to store the sensor status (value)*/,
    myCanId: 0x68,
    effectivelyEnabled: true, /*false = off; true = on; mirror value: relayState*/
    deviceType: 2
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

  pinMode(buzzerPin, OUTPUT); // Set buzzer pin as output

  //initialize the device pins (inputs and relay, if applicable)
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
  
  delay(100); //wait for relay to actually click into place
}

void setDeviceEnableState(int deviceNumber, bool newState)
{
  if (newState == true && devices[deviceNumber].effectivelyEnabled == false)
  {
    devices[deviceNumber].effectivelyEnabled = true;
    if (devices[deviceNumber].relayPin != -1) {
      Serial.println(">>>>>>>>>>>ENABLING RELAY>>>>>>>>>>>");
      digitalWrite(devices[deviceNumber].relayPin, LOW); // low = on
      delay(100); //delay sending anything while the sensor gets power and begins reading an OK value while powering up
    } else {
      Serial.println(">>>>>>>>>>>ENABLING LOGICAL DEVICE>>>>>>>>>>>");
    }
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
  
  if (devices[deviceNumber].effectivelyEnabled == true && devices[deviceNumber].sensorVal == HIGH) {
    myCanMessage.data[1] = 0xAA; // alarm
  } else if (devices[deviceNumber].effectivelyEnabled == true && devices[deviceNumber].sensorVal == LOW) {
    myCanMessage.data[1] = 0x00; // ok
  } else if (devices[deviceNumber].effectivelyEnabled == false) {
    myCanMessage.data[1] = 0xFF;
  }
}

void sendMessage(int deviceNumber, int message)
{
  makeMessage(deviceNumber, message);
  mcp2515.sendMessage(&myCanMessage);

  Serial.print(myCanMessage.data[1], HEX);

  Serial.print(" sent to 0x");
  Serial.print(myCanMessage.data[0], HEX);
  Serial.print(" from 0x");
  Serial.println(devices[deviceNumber].myCanId, HEX);
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
      return -1000; //broadcast
    }
    for (int i = 0; i < numDevices; i++) {
      if (incomingCanMsg.data[0] == devices[i].myCanId) { //received message has recipient specified as one of the devices in "devices"
        return i; //device array index in devices
      }
    }
  }
  return -1; //unmatched~no such device
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
  if (readIncomingCanMessage())
  {
    Serial.println(">>>>>>>READMESSAGE TRUE");
    Serial.print(">>>>>>>MESSAGE: ");
    debugPrintIncoming();
    processIncomingCanMessage();
  }


  buzzerSounding = false;
  for (int i = 0; i < numDevices; i++) {
    devices[i].sensorVal = digitalRead(devices[i].sensorPin); /*LOW by default, no motion detected*/
    buzzerSounding = buzzerSounding || (devices[i].sensorVal && devices[i].effectivelyEnabled == true);
  }

  long now = millis();

  if (enableBuzzer && buzzerSounding && now - previousMillis >= toneInterval) {
    previousMillis = now; // Update the time

    // Play the tone at the current frequency
    tone(buzzerPin, frequency);

    // Update the frequency
    if (increasing) {
      frequency += 10;
      if (frequency >= 2000) {
        increasing = false; // Start decreasing the frequency
      }
    } else {
      frequency -= 10;
      if (frequency <= 500) {
        increasing = true; // Start increasing the frequency
      }
    }
  } else if (enableBuzzer && !buzzerSounding) {
    noTone(buzzerPin);
  }
  
  if ((now > lastSentMillis + sendEveryMillis) || now < lastSentMillis && now > sendEveryMillis)
  { // only send a message if it's been "sendEveryMillis" OR the timer has cycled around LONG
    sendMessage(loopDeviceIndex,0);
    lastSentMillis = now;
    if (loopDeviceIndex == numDevices-1) {
      loopDeviceIndex = 0;
    } else {
      loopDeviceIndex++;
    }
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
