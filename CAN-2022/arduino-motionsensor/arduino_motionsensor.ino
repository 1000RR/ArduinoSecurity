#include <SPI.h>
#include <mcp2515.h>

struct can_frame myCanMessage;
MCP2515 mcp2515(10);
MCP2515::ERROR canMessageError;

// int led = 13;                // the pin that the LED is atteched to
int sensorPin = 5; // the pin that the sensor is atteched to
int state = LOW;   // by default, no motion detected
int sensorVal = 0; // variable to store the sensor status (value)
int relayPin = 6;
int myCanId = 0x80;
const int BROADCAST_ADDR = 0x00;
int homebaseCanId = 0x14;
bool relayState = true; // false = off; true = on; MUST BE SET SAME AS effectivelyEnabled
bool effectivelyEnabled = true;
struct can_frame incomingCanMsg;
String ERROR_NAMES[] = {"OK", "FAIL", "ALLTXBUSY", "FAILINIT", "FAILTX", "NOMSG"};
long lastSentMillis = 0;

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
  pinMode(relayPin, OUTPUT);
  if (effectivelyEnabled == true)
  {
    digitalWrite(relayPin, LOW); // low = on
  }
  else
  {
    digitalWrite(relayPin, HIGH); // high = off
  }

  // first 0x75 hall
  // second 0x80 garage (hipower)
  myCanMessage.can_id = myCanId;
  myCanMessage.can_dlc = 3;
  myCanMessage.data[0] = homebaseCanId;
  myCanMessage.data[1] = 0x00;
  myCanMessage.data[2] = 0x02;

  Serial.println("Example: Write to CAN");
}

void setRelayState(bool state)
{
  if (state == true && relayState == false)
  {
    relayState = true;
    digitalWrite(relayPin, LOW); // low = on
    Serial.println(">>>>>>>>>>>ENABLING RELAY>>>>>>>>>>>");
    // delay(100); //delay sending anything while the sensor gets power and begins reading an OK value while powering up
    effectivelyEnabled = true;
  }
  else if (state == false && relayState == true)
  {
    relayState = false;
    Serial.println(">>>>>>>>>>>DISABLING RELAY>>>>>>>>>>>");
    digitalWrite(relayPin, HIGH); // high = off
    effectivelyEnabled = false;
  }
}

void makeMessage(bool override, int message)
{
  if (!override)
  {
    sensorVal = digitalRead(sensorPin);
    // Serial.print(sensorVal);
  }
  else
  {
    Serial.print("not reading sensor val - message override");
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

  Serial.print("Message sent to 0x");
  Serial.print(myCanMessage.data[0], HEX);
  Serial.print(" from 0x");
  Serial.print(myCanId, HEX);
  Serial.print(" message: ");
  Serial.println(myCanMessage.data[1], HEX);
}

bool readMessage()
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
      // Serial.print("INCOMING CAN MESSAGE ERROR: ");
      // Serial.println(ERROR_NAMES[canMessageError]);
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

void processMessage()
{
  if (matchMessageToThisDevice() == true)
  {
    if (incomingCanMsg.data[1] == 0x0F)
    { // enable
      setRelayState(true);
    }
    else if (incomingCanMsg.data[1] == 0x01)
    { // disable
      setRelayState(false);
    }
  }
}

void loop()
{
  Serial.print(">>>> effectively enabled: ");
  Serial.print(effectivelyEnabled);
  Serial.print(" || relay state: ");
  Serial.println(relayState);

  if (readMessage())
  {
    Serial.println(">>>>>>>READMESSAGE TRUE");
    Serial.print(">>>>>>>MESSAGE: ");
    debugPrintIncoming();
    processMessage();
  }
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
  Serial.println(output);
}
