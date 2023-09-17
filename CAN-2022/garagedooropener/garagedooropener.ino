#include <SPI.h>
#include <mcp2515.h>

bool debug = true ; //debug output printing to Serial
bool suppressErrorDebugText = true; //debug output
struct can_frame incomingCanMsg;
struct can_frame myCanMessage;
struct MessageStruct {
    int id;
    int addressee;
    int message;
    int deviceType;
};
MCP2515 mcp2515(10);
String ERROR_NAMES[] = {"OK", "FAIL", "ALLTXBUSY", "FAILINIT", "FAILTX", "NOMSG"};
const int ID_NOT_USED = -1;
int myCanId = 0xD0;
int relayPin = 7;
int alarmVaribleDevicePin = 17; //17 is A3. A0 is 14, etc.
long loopIndexMax = 30000;
long sendEveryXLoops = 10000; //tied to loopIndexMax
int deviceType = 3;
const int BROADCAST_ADDR = 0x00;
MCP2515::ERROR canMessageError;
long loopIndex = 0;
int currentStatus = 0x00;

///MSG FORMAT: [0] TO (1 byte, number = specific ID OR 00 = broadcast)
///            [1] MSG (1 byte)
///            [2] DEVICETYPE (1 byte) 
///SENSOR MESSAGE DICTIONARY (00 - enabled and status ok, AA - enabled and status alarmed, BB - enable alarm device, CC - reset alarm, FF - disabled)
///HOME BASE MESSAGE DICTIONARY (0F - enable yourself, O1 - disable yourself)
///DEVICE TYPE DICTIONARY: (01 controller, 02 pir/microwave alarm, 03 bell, 04 visual alarm, 05 door open sensor)
///HOME BASE CAN ID = 0x14;

//enum ERROR {
//    ERROR_OK        = 0,
//    ERROR_FAIL      = 1,
//    ERROR_ALLTXBUSY = 2,
//    ERROR_FAILINIT  = 3,
//    ERROR_FAILTX    = 4,
//    ERROR_NOMSG     = 5
//}

void setup() {
  pinMode(relayPin, OUTPUT);
  
  Serial.begin(115200);
  
  mcp2515.reset();
  mcp2515.setBitrate(CAN_125KBPS);
  mcp2515.setNormalMode();
}

void loop() {
  //check for all expected senders trigger if sender is deeemed to not have responded in a while (determine), or is explicitly alarmed.
  //this can be done by keeping a list of unique identifiers burned into each sender and periodically expecting messages from them
  //must be able to reset trip for (determine) with the push of a button

  if (loopIndex % sendEveryXLoops == 0) { //every so often, let bus know this device exists
    sendMessage(0x00, currentStatus, myCanId, deviceType); //bell is ok
  }

  canMessageError = mcp2515.readMessage(&incomingCanMsg);

  if (canMessageError == MCP2515::ERROR_OK) {
    if (incomingCanMsg.can_id == 0x14 && incomingCanMsg.data[0] == myCanId && incomingCanMsg.data[1] == 0x0D) { //if home base addresses to me and message is 0x0D, toggle relay for a small innerval
      setConstantOnAlarmPinValue(true);
      delay(500);
      setConstantOnAlarmPinValue(false);
    }

    if (debug) {
      Serial.print("CAN MSG RECEIVED");

      Serial.print("0x");
      Serial.print(incomingCanMsg.can_id, HEX);
      Serial.print("-0x");
      Serial.print(incomingCanMsg.data[0], HEX);
      Serial.print("-0x");
      Serial.print(incomingCanMsg.data[1], HEX);
      Serial.print("-0x");
      Serial.print(incomingCanMsg.data[2], HEX);
      Serial.print("\n");
      Serial.flush();
    }

  } else {
    if (debug && !suppressErrorDebugText) {
      Serial.print("ERROR READING CAN: ");
      Serial.println(ERROR_NAMES[canMessageError]);
    }
  }
  if (loopIndex < loopIndexMax-1) loopIndex++;
  else loopIndex = 0;
  
  if (debug && loopIndex % sendEveryXLoops == 0) {Serial.print("loopIndex "); Serial.println(loopIndex);}
}

void setConstantOnAlarmPinValue(bool state) {
  digitalWrite(relayPin, state ? HIGH : LOW);
}

//COMMON
MessageStruct parseIncomingCanMessage() {
  MessageStruct messageStruct;

  messageStruct.id = incomingCanMsg.can_id;
  messageStruct.addressee = incomingCanMsg.data[0];
  messageStruct.message = incomingCanMsg.data[1];
  messageStruct.deviceType = incomingCanMsg.data[2];

  return messageStruct;
}

void _makeMessage(int message, int addressee, int myCanId, int myDeviceType) {
  myCanMessage.can_id  = myCanId;
  myCanMessage.can_dlc = 3;
  myCanMessage.data[0] = addressee;
  myCanMessage.data[1] = message;
  myCanMessage.data[2] = myDeviceType;
}

void sendMessage(int message, int addressee, int myCanId, int myDeviceType) {
  _makeMessage(message, addressee, myCanId, myDeviceType);
  mcp2515.sendMessage(&myCanMessage);
}
