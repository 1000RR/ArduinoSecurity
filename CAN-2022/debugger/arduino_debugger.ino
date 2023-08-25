#include <SPI.h>
#include <mcp2515.h>

bool debug = true;
struct can_frame incomingCanMsg;
MCP2515 mcp2515(10);
String ERROR_NAMES[] = {"OK", "FAIL", "ALLTXBUSY", "FAILINIT", "FAILTX", "NOMSG"};
MCP2515::ERROR canMessageError;


///MSG FORMAT: [0] TO (1 byte, number = specific ID OR 00 = broadcast)
///            [1] MSG (1 byte)
///SENSOR MESSAGE DICTIONARY (00 - enabled and status ok, AA - enabled and status alarmed, FF - disabled)
///HOME BASE MESSAGE DICTIONARY (0F - enable yourself, O1 - disable yourself)
///HOME BASE CAN ID = 0x14;


void setup() {
  Serial.begin(115200);
  
  mcp2515.reset();
  mcp2515.setBitrate(CAN_125KBPS);
  mcp2515.setNormalMode();
}

void loop() {
  canMessageError = mcp2515.readMessage(&incomingCanMsg);
  if (canMessageError == MCP2515::ERROR_OK) {
    debugPrintData();
  } else {
    if (debug && canMessageError != MCP2515::ERROR_NOMSG) {
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
  delay(5);
}


void debugPrintData() {
    if (debug == false) return;

    Serial.print(incomingCanMsg.can_id, HEX); // print ID
    Serial.print(" "); 
    Serial.print(incomingCanMsg.can_dlc, HEX); // print DLC
    Serial.print(" ");

    for (int i = 0; i < incomingCanMsg.can_dlc; i++)  {  // print the data
      Serial.print(incomingCanMsg.data[i], HEX);
      Serial.print(" ");
    }
    Serial.println(" ");
}
