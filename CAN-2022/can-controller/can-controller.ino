#include <SPI.h>
#include <mcp2515.h>
#include <ssd1306.h>

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
MCP2515::ERROR canMessageError;
int index; //used for message number in testing
String incomingComMessage;
MessageStruct parsedIncomingComMessage;
int armedLedPin = 3; //blue led
int disarmedLedPin = 2; //red led
int armedButtonPin = 9;
int homeBaseCanId = 0x14;
int previousArmedButtonState = HIGH;
int loopIndex = 0;
bool currentArmedButtonState;
bool armedStatus = false;
bool alarmedStatus = false;
String strActiveAlarmedDevicesIdList = "";
String strAllAlarmedDevicesIdList = "";
int outputToOledEveryXloops = 10;

///MSG FORMAT: [0] TO (1 byte, number = specific ID OR 00 = broadcast)
///            [1] MSG (1 byte)
///            [2] DEVICETYPE (1 byte) 
///SENSOR MESSAGE DICTIONARY (00 - enabled and status ok, AA - enabled and status alarmed, BB - trigger alarm device, CC - reset alarm, FF - disabled)
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
  Serial.begin(115200);
  Serial.setTimeout(10);
  
  mcp2515.reset();
  mcp2515.setBitrate(CAN_125KBPS);
  mcp2515.setNormalMode();

  setupOled();
  setupArmedLeds();
  setupArmedButtonPin();

  lcdHello();
}

void doLocalThingsWithMessage(MessageStruct message) {
  if (message.message == 0xD1) { //turn on ARMED led, turn off DISARMED led
    armedStatus = true;
    setArmedLedPin(armedStatus);
    setDisarmedLedPin(!armedStatus);
  } else if (message.message == 0xD0) { //turn on DISARMED led, turn off ARMED led
    armedStatus = false;
    alarmedStatus = false;
    strActiveAlarmedDevicesIdList = "";
    strAllAlarmedDevicesIdList = "";
    setArmedLedPin(armedStatus);
    setDisarmedLedPin(!armedStatus);
  } else if (message.addressee == 0xFF && message.message == 0xA0) { //home base sending its arduino the ID of a device that's causing the alarm (single device / message)
      alarmedStatus = true;
      if (strActiveAlarmedDevicesIdList.indexOf("0x" + String(message.deviceType, HEX)) == -1) {
        strActiveAlarmedDevicesIdList += ("0x" + String(message.deviceType, HEX) + " ");
      }
      if (strAllAlarmedDevicesIdList.indexOf("0x" + String(message.deviceType, HEX)) == -1) {
        strAllAlarmedDevicesIdList += ("0x" + String(message.deviceType, HEX) + " ");
      }
  } else if (message.addressee == 0xFF && message.message == 0xB0) { //home base sending its arduino the ID of a device that's not causing the alarm (single device / message)
        index = strActiveAlarmedDevicesIdList.indexOf("0x" + String(message.deviceType, HEX));
        if (index > -1) {
          strActiveAlarmedDevicesIdList.remove(index, 5); //erase 5 chars
        }
  } else if (message.addressee == 0xFF && message.message == 0xC0) { //home base sending its arduino a signal to turn off alarmedStatus
      alarmedStatus = false;
      strActiveAlarmedDevicesIdList = "";
      strAllAlarmedDevicesIdList = "";
  }
}

void setupOled(){
  ssd1306_setFixedFont(ssd1306xled_font6x8);
  ssd1306_128x32_i2c_init();
  ssd1306_clearScreen();
}

void setupArmedLeds() {
  pinMode(armedLedPin, OUTPUT);
  pinMode(disarmedLedPin, OUTPUT);
}

void setupArmedButtonPin() {
  pinMode(armedButtonPin, INPUT_PULLUP);
}

void setArmedLedPin(bool value) {
  if (value == true)
    digitalWrite(armedLedPin, HIGH); //low = off, when led+ connected to digital out pin, led- connected to GND
  else
    digitalWrite(armedLedPin, LOW); //high = on, when led+ connected to digital out pin, led- connected to GND
}

void setDisarmedLedPin(bool value)
{
  if (value == true)
    digitalWrite(disarmedLedPin, HIGH); //low = off, when led+ connected to digital out pin, led- connected to GND
  else
    digitalWrite(disarmedLedPin, LOW); //high = on, when led+ connected to digital out pin, led- connected to GND
}

void loop() {
  //retrieve incoming frames from COM, and send via CAN
  Serial.flush();
  incomingComMessage = Serial.readStringUntil('\n');
  if (incomingComMessage.length() > 0) {
    parsedIncomingComMessage = parseIncomingComMessage(incomingComMessage);
    doLocalThingsWithMessage(parsedIncomingComMessage);
    if (parsedIncomingComMessage.addressee != 0xFF) //has to be addressed to not the home base's arduino
      sendMessage(parsedIncomingComMessage.id, parsedIncomingComMessage.addressee, parsedIncomingComMessage.message, parsedIncomingComMessage.deviceType);
  }

  currentArmedButtonState = digitalRead(armedButtonPin);
  
  if (currentArmedButtonState != previousArmedButtonState)
  { // button pressed - send serial armed toggle button press message to raspi
    if (currentArmedButtonState == LOW) {
      previousArmedButtonState = LOW;
      Serial.print("0x");
      Serial.print(homeBaseCanId, HEX);
      Serial.print("-0x");
      Serial.print(homeBaseCanId, HEX);
      Serial.print("-0x");
      Serial.print(0xEE, HEX);
      Serial.print("-0x");
      Serial.print(0x01, HEX);
      Serial.print("\n");
      Serial.flush();
    } else {
      previousArmedButtonState = HIGH;
    }
  }

  canMessageError = mcp2515.readMessage(&incomingCanMsg);
  if (canMessageError == MCP2515::ERROR_OK) {
    //retrieve from CAN frame(s), and send to COM via Serial
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

    //use this structure to access data: incomingCanMsg.data[1]==0xAA
    //maybe delay too??? delay(DELAY_LOOP_TIME);
  }
  
  outputToLcd(loopIndex);
  if (alarmedStatus == true) blinkDisarmedLed(loopIndex);
  else if (armedStatus == true) setDisarmedLedPin(false);

  if (loopIndex < 32766) {
    loopIndex++;
  } else {
    loopIndex = 0;
  }
}

//void debugPrintData() {
//    if (debug == false) return;
//
//    Serial.print(incomingCanMsg.can_id, HEX); // print ID
//    Serial.print(" "); 
//    Serial.print(incomingCanMsg.can_dlc, HEX); // print DLC
//    Serial.print(" ");
//
//    for (int i = 0; i < incomingCanMsg.can_dlc; i++)  {  // print the data
//      Serial.print(incomingCanMsg.data[i], HEX);
//      Serial.print(" ");
//    }
//    Serial.println(" ");
//}

//COMMON
MessageStruct parseIncomingComMessage(String message) {
  MessageStruct messageStruct;
  char * token;
  char delimiter = '-';
  int ind = 0;
  char messageInChars [64]; 
  message.toCharArray(messageInChars, message.length());

  token = strtok(&(messageInChars[0]), &delimiter);

   while (token != NULL && ind < 4) {
//      Serial.print(">>> incoming arg parsing ");
//      Serial.print(strtol(token, NULL, 16), HEX);
//      Serial.print("\n");
      if (ind == 0) messageStruct.id = strtol(token, NULL, 16); 
      else if (ind == 1) messageStruct.addressee = strtol(token, NULL, 16);
      else if (ind == 2) messageStruct.message = strtol(token, NULL, 16);
      else if (ind == 3) messageStruct.deviceType = strtol(token, NULL, 16);
      ind++;
      token=strtok(NULL, &delimiter);
   }

  return messageStruct;
}

// MessageStruct parseIncomingCanMessage() {
//   MessageStruct messageStruct;

//   messageStruct.id = incomingCanMsg.can_id;
//   messageStruct.addressee = incomingCanMsg.data[0];
//   messageStruct.message = incomingCanMsg.data[1];
//   messageStruct.deviceType = incomingCanMsg.data[2];

//   return messageStruct;
// }

void _makeMessage(int myCanId, int addressee, int message, int myDeviceType) {
  myCanMessage.can_id  = myCanId;
  myCanMessage.can_dlc = 3;
  myCanMessage.data[0] = addressee;
  myCanMessage.data[1] = message;
  myCanMessage.data[2] = myDeviceType;
}

void sendMessage(int myCanId, int addressee, int message, int myDeviceType) {
  _makeMessage(myCanId, addressee, message, myDeviceType);
  mcp2515.sendMessage(&myCanMessage);
//  if (debug) {
//    Serial.print("Messages sent ");
//    Serial.print(myCanMessage.data[0], HEX);
//    Serial.println(myCanMessage.data[1], HEX);
//  }
}

void lcdHello() {
  ssd1306_invertMode();
  ssd1306_setFixedFont(ssd1306xled_font8x16);
  ssd1306_printFixed(0, 8, "     BOBIK", STYLE_BOLD);
  delay(3000);
  ssd1306_normalMode();
  ssd1306_clearScreen();
}

void outputToLcd(int loopIndex)
{
    ssd1306_setFixedFont(ssd1306xled_font6x8);
    if (loopIndex % outputToOledEveryXloops != 0)
      return;

    //first line
    String strArmedStatus = armedStatus == true ? "ENABLED              " : "DISABLED              ";
    String strOutput;
    // ssd1306_printFixed(0,  8, "Normal text", STYLE_NORMAL);
    // ssd1306_printFixed(0, 16, "Bold text", STYLE_BOLD);
    // ssd1306_printFixed(0, 24, "Italic text", STYLE_ITALIC);
    if (armedStatus == true) ssd1306_negativeMode();
    ssd1306_printFixed(0, 0, &strArmedStatus[0], STYLE_NORMAL);
    ssd1306_printFixed(96, 0, &(((String)loopIndex)[0]), STYLE_ITALIC);
    if (armedStatus == true) ssd1306_positiveMode();

    //second line & potentially third line
    if (alarmedStatus == true) {
      if (loopIndex % 3 == 0) ssd1306_negativeMode();
      ssd1306_printFixed(0, 8, "        ALARM        ", STYLE_BOLD);
      if (loopIndex % 3 == 0) ssd1306_positiveMode();
      if (strActiveAlarmedDevicesIdList != "") {
        strOutput = strActiveAlarmedDevicesIdList + "                        ";
        ssd1306_printFixed(0, 16, &strOutput[0], STYLE_BOLD); // third line
      }
      if (strAllAlarmedDevicesIdList != "") {
        strOutput = strAllAlarmedDevicesIdList + "                        ";
        ssd1306_printFixed(0, 24, &strOutput[0], STYLE_BOLD); // third line
      }
    } else {
       ssd1306_printFixed(0, 8, "      NO ALARM       ", STYLE_BOLD);
       ssd1306_printFixed(0, 16, "                     ", STYLE_BOLD); // third line
       ssd1306_printFixed(0, 24, "                     ", STYLE_BOLD); // fourth line
    }
}

void blinkDisarmedLed (int loopIndex) {
  setDisarmedLedPin(!digitalRead(disarmedLedPin));
}
