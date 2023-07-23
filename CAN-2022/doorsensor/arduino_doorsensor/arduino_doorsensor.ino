#include <SPI.h>
#include <mcp2515.h>

struct can_frame myCanMessage;
MCP2515 mcp2515(10);
MCP2515::ERROR canMessageError;

// int led = 13;                // the pin that the LED is atteched to
int sensorPin = 5; // the pin that the sensor is atteched to
int state = LOW;   // by default, no motion detected
int sensorVal = 0; // variable to store the sensor status (value)
int myCanId = 0x30;
const int BROADCAST_ADDR = 0x00;
int homebaseCanId = 0x14;
bool effectivelyEnabled = true;
struct can_frame incomingCanMsg;
String ERROR_NAMES[] = {"OK", "FAIL", "ALLTXBUSY", "FAILINIT", "FAILTX", "NOMSG"};
long lastSentMillis = 0;
bool debug = false;

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
  while (!Serial)
    ;
  Serial.begin(115200);

  mcp2515.reset();
  mcp2515.setBitrate(CAN_125KBPS);
  mcp2515.setNormalMode();

  // pinMode(led, OUTPUT);      // initalize LED as an output
  pinMode(sensorPin, INPUT_PULLUP); // initialize sensor as an input


  // first 0x75 hall
  // second 0x80 garage (hipower)
  myCanMessage.can_id = myCanId;
  myCanMessage.can_dlc = 3;
  myCanMessage.data[0] = homebaseCanId;
  myCanMessage.data[1] = 0x00;
  myCanMessage.data[2] = 0x02;

  if (debug == true) Serial.println("Example: Write to CAN");
}

void setEnabledState(bool state)
{
  if (state == true && effectivelyEnabled == false)
  {
    effectivelyEnabled = true;
  }
  else if (state == false && effectivelyEnabled == true)
  {
    effectivelyEnabled = false;
  }
}

void makeMessage(bool override, int message)
{
  if (!override)
  {
    sensorVal = digitalRead(sensorPin); 
    if (debug == true) Serial.print("SENSOR VALUE=======");
    if (debug == true) Serial.print(sensorVal);
  }
  else
  {
    if (debug == true) Serial.print("not reading sensor val - message override");
  }

  myCanMessage.data[0] = homebaseCanId;
  if (override)
  {
    myCanMessage.data[1] = message;
  }
  else if (effectivelyEnabled == true && sensorVal == 1)
  {
    // digitalWrite(led, HIGH);
    myCanMessage.data[1] = 0xAA; // alarm
  }
  else if (effectivelyEnabled == true && sensorVal == 0)
  {
    // digitalWrite(led, LOW);
    myCanMessage.data[1] = 0x00; // ok
  }
  else if (effectivelyEnabled == false)
  {
    myCanMessage.data[1] = 0xFF;
  }
}

void sendMessage(bool override, int message)
{
  makeMessage(override, message);
  mcp2515.sendMessage(&myCanMessage);

  if (debug == true) Serial.print("Messages sent ");
  if (debug == true) Serial.print(myCanMessage.data[0], HEX);
  if (debug == true) Serial.println(myCanMessage.data[1], HEX);
}

bool readMessage()
{
  for (int i = 0; i < 250; i++)
  {
    canMessageError = mcp2515.readMessage(&incomingCanMsg);
    if (canMessageError == MCP2515::ERROR_OK)
    {
      if (incomingCanMsg.can_id == homebaseCanId)
      {
        return true;
      }
    }
    else
    {
      // if (debug == true) Serial.print("INCOMING CAN MESSAGE ERROR: ");
      // if (debug == true) Serial.println(ERROR_NAMES[canMessageError]);
    }
    delay(1);
  }

  return false;
}

bool matchMessageToThisDevice()
{
  if (incomingCanMsg.can_id == homebaseCanId)
  { // from home base
    if (incomingCanMsg.data[0] == myCanId || incomingCanMsg.data[0] == BROADCAST_ADDR)
    { // me or all devices
      return true;
    }
  }
  return false;
}

bool processMessage()
{
  if (matchMessageToThisDevice() == true)
  {
    if (incomingCanMsg.data[1] == 0x0F)
    { // enable
      setEnabledState(true);
      return 0; // don't send a message back
    }
    else if (incomingCanMsg.data[1] == 0x01)
    { // disable
      setEnabledState(false);
      return 0; // dont send a message back
    }
  }
  else
  {
    return 1;
  }
}

void loop()
{
  if (debug == true) Serial.print(">>>> effectively enabled: ");
  if (debug == true) Serial.print(effectivelyEnabled);


  bool needToReply = true;
  if (readMessage())
  {
    if (debug == true) Serial.println(">>>>>>>READMESSAGE TRUE");
    if (debug == true) Serial.print(">>>>>>>MESSAGE: ");
    debugPrintIncoming();
    needToReply = processMessage();
  }
  // if (needToReply == true) {
  long now = millis();
  if ((now > lastSentMillis + 500) || now < lastSentMillis)
  { // only send a message if it's been 500ms OR the timer has cycled around LONG
    sendMessage(false, 0);
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
  if (debug == true) Serial.println(output);
}