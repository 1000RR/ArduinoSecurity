#include <SPI.h>
#include <mcp2515.h>

bool debug = false; //debug output printing to Serial

struct can_frame incomingCanMsg;
struct can_frame myCanMessage;
MCP2515 mcp2515(10);
String ERROR_NAMES[] = {"OK", "FAIL", "ALLTXBUSY", "FAILINIT", "FAILTX", "NOMSG"};
const int ID_NOT_USED = -1;
const int DEVICE_CYCLES_START_CONST = -1;
int myCanId = 0x14;
int switchPin = 5;
int buzzerPin = 7;
int armedLedPin = 6;
int buzzerBaseFreq = 2500;
int buzzerCount = 0;
int MAX_STEPS = 4;
typedef struct {
  int id = 0; //if zero, treated as not present by the rest of the code
  String name; 
  int receivedCyclesAgo = DEVICE_CYCLES_START_CONST; //-1 just to be safe in case MAX_CYCLES_BEFORE_ALARM is 1.
} pirDeviceDetails;
const int DEVICES_LENGTH = 25;
const int MAX_CYCLES_BEFORE_ALARM = 50; // roughly MAX_STEPS * MAX_CYCLES_BEFORE_ALARM * DELAY_LOOP_TIME is the ms timeout after which the alarm will go off in the absence of messages from a specific can device
const int DELAY_LOOP_TIME = 50;
pirDeviceDetails alarmDevices[DEVICES_LENGTH];
bool alarmed = false;
bool switchPinValue = LOW;
MCP2515::ERROR canMessageError;
bool lastSwitchState = true; // assumes that MOTION SENSORS ARE DEFAULT ON!!!!
bool messageSenderNeedsToBeAdded = true;

///MSG FORMAT: [0] TO (1 byte, number = specific ID OR 00 = broadcast)
///            [1] MSG (1 byte)
///            [2] DEVICETYPE (1 byte) 
///SENSOR MESSAGE DICTIONARY (00 - enabled and status ok, AA - enabled and status alarmed, FF - disabled)
///HOME BASE MESSAGE DICTIONARY (0F - enable yourself, O1 - disable yourself)
///DEVICE TYPE DICTIONARY: (01 - controller, 02 - pir alarm)
///HOME BASE CAN ID = 0x14;


void setup() {
  pinMode(buzzerPin, OUTPUT);
  pinMode(switchPin, INPUT_PULLUP);
  pinMode(armedLedPin, INPUT_PULLUP);
  
  Serial.begin(115200);
  
  mcp2515.reset();
  mcp2515.setBitrate(CAN_125KBPS);
  mcp2515.setNormalMode();

  if (debug) {
    Serial.println("------- CAN Read ----------");
    Serial.println("ID  DLC   DATA");
  }

  initDevicesArray();
}

void loop() {
  //check for all expected senders trigger if sender is deeemed to not have responded in a while (determine), or is explicitly alarmed.
  //this can be done by keeping a list of unique identifiers burned into each sender and periodically expecting messages from them
  //must be able to reset trip for (determine) with the push of a button

  switchPinValue = digitalRead(switchPin);
  possiblyReactToSwitchStateChange(lastSwitchState, switchPinValue);
  canMessageError = mcp2515.readMessage(&incomingCanMsg);

  //CURRENTLY SET UP FOR ONE SENDER. 0x00 messages (at rest) from other devices will inhibit the alarm on the receiving side.
  if (switchPinValue == HIGH) {
     digitalWrite(armedLedPin, HIGH);
  } else {
    digitalWrite(armedLedPin, LOW);
  }

  if (canMessageError == MCP2515::ERROR_OK) {
    debugPrintData();
    messageSenderNeedsToBeAdded = true;

    for (int i = 0; i < DEVICES_LENGTH; i++) {
      if (alarmDevices[i].id != ID_NOT_USED && incomingCanMsg.can_id == alarmDevices[i].id) { //found item
        messageSenderNeedsToBeAdded = false;
        if (switchPinValue == HIGH && incomingCanMsg.data[1]==0xAA) { 
          alarmed = true;
          resetPresenceCounterForDevice(i);
        } else if (incomingCanMsg.data[1] == 0x00 || incomingCanMsg.data[1] == 0xFF) { //catch-all: any type of message that isn't ALARMED; for purposes of device connection tracking
          resetPresenceCounterForDevice(i);
        }
      }
    }

    if (messageSenderNeedsToBeAdded) { //message sender not found, add to registry
      for (int i=0; i < DEVICES_LENGTH; i++) {
        if (alarmDevices[i].id == ID_NOT_USED) {
          if (debug) {
            String output = ">>>>>ADDING NEW CAN DEVICE ID: " + incomingCanMsg.can_id;
            Serial.println(output);
          }
          alarmDevices[i].id = incomingCanMsg.can_id;
          resetPresenceCounterForDevice(i);
          break;
        }
      }
    }
  } else {
    if (debug) {
      Serial.print("ERROR READING CAN: ");
      Serial.println(ERROR_NAMES[canMessageError]);
    }

    //enum ERROR {
    //    ERROR_OK        = 0,
    //    ERROR_FAIL      = 1,
    //    ERROR_ALLTXBUSY = 2,
    //    ERROR_FAILINIT  = 3,
    //    ERROR_FAILTX    = 4,
    //    ERROR_NOMSG     = 5
    //}
  }

  for (int i = 0; i < DEVICES_LENGTH; i++) {
    if (alarmDevices[i].id != ID_NOT_USED) {
      alarmDevices[i].receivedCyclesAgo++;
      if (debug) {
        String output = "Last saw device " + String(alarmDevices[i].id) + " " + String(getPresenceCycleCountForDevice(i)) + " cycles ago";
        Serial.println(output);
      }
      if (getPresenceCycleCountForDevice(i) > MAX_CYCLES_BEFORE_ALARM) {
        String output = "ALARMED DUE TO " + String(alarmDevices[i].id) + " missing for " + String(getPresenceCycleCountForDevice(i)) + " cycles";
        Serial.println(output);
        alarmed = true;
      }
    }
  }

  maybeTone();
  lastSwitchState = switchPinValue;
}

void possiblyReactToSwitchStateChange(bool last, bool current) {
  if (last != current) {
    if (current == true) {
      if (debug) {
        Serial.println("SWITCH NOW ON");
      }
      sendBroadcastMessage(0x0F); //enable command
    } else {
      if (debug) {
        Serial.println("SWITCH NOW OFF");
      }
      sendBroadcastMessage(0x01); //disable command
    }
  }
}

//the following function depends on the state of the switch && the alarmed value
void maybeTone() {
  if (alarmed == true && switchPinValue == HIGH) {
    if (buzzerCount == MAX_STEPS) {
      buzzerCount = 1;
    } else {
      buzzerCount++;
    }

    tone(buzzerPin, buzzerBaseFreq * (buzzerCount > (MAX_STEPS/2) ? 2 : 1));
 
  } else if (switchPinValue == LOW) {
    alarmed = false;
    buzzerCount = 1;
    noTone(buzzerPin);
  }
  delay(DELAY_LOOP_TIME);
}

void initDevicesArray() {
  for (int i = 0; i < DEVICES_LENGTH; i++) {
    alarmDevices[i].id = ID_NOT_USED;
    alarmDevices[i].name = "";
    resetPresenceCounterForDevice(i);
  }
}

void debugPrintData() {
    if (debug == false) return;

    String output = "ID " + String(incomingCanMsg.can_id, HEX) + " DATA SIZE " + String(incomingCanMsg.can_dlc, HEX) + " ";
    Serial.print(output);

    for (int i = 0; i < incomingCanMsg.can_dlc; i++)  {  // print the data
      Serial.print(incomingCanMsg.data[i], HEX);
      Serial.print(" ");
    }
    Serial.println(" ");
}

void resetPresenceCounterForDevice(int deviceIndex) { //reset the device message counter to this value
  alarmDevices[deviceIndex].receivedCyclesAgo = DEVICE_CYCLES_START_CONST;
}

int getPresenceCycleCountForDevice(int deviceIndex) { //how many cycles ago this device (by array index) sent the last message; DEVICE_CYCLES_START_CONST is a special value
  return alarmDevices[deviceIndex].receivedCyclesAgo;
}

void makeBroadcastMessage(int message) {
  myCanMessage.can_id  = myCanId;
  myCanMessage.can_dlc = 2;
  myCanMessage.data[0] = 0x00; //broadcast
  myCanMessage.data[1] = message;
  
}

void sendBroadcastMessage(int message) {
  makeBroadcastMessage(message);
  mcp2515.sendMessage(&myCanMessage);

  if (debug) {
    Serial.print("Messages sent ");
    Serial.print(myCanMessage.data[0], HEX);
    Serial.println(myCanMessage.data[1], HEX);
  }

  delay(25);
}
