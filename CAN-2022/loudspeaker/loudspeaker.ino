/*************************************************** 
  This is an example for the Adafruit VS1053 Codec Breakout

  Designed specifically to work with the Adafruit VS1053 Codec Breakout 
  ----> https://www.adafruit.com/products/1381

  Adafruit invests time and resources providing this open source code, 
  please support Adafruit and open-source hardware by purchasing 
  products from Adafruit!

  Written by Limor Fried/Ladyada for Adafruit Industries.  
  BSD license, all text above must be included in any redistribution
 ****************************************************/

// include SPI, MP3 and SD libraries
#include <SPI.h>
#include <Adafruit_VS1053.h>
#include <SD.h>
#include <mcp2515.h>

// define the pins used
//#define CLK 13       // SPI Clock, shared with SD card
//#define MISO 12      // Input data, from VS1053/SD card
//#define MOSI 11      // Output data, to VS1053/SD card
// Connect CLK, MISO and MOSI to hardware SPI pins. 
// See http://arduino.cc/en/Reference/SPI "Connections"


// These are the pins used for the music maker shield
#define SHIELD_RESET  -1      // VS1053 reset pin (unused!)
#define SHIELD_CS     7      // VS1053 chip select pin (output)
#define SHIELD_DCS    6      // VS1053 Data/command select pin (output)

// These are common pins between breakout and shield
#define CARDCS 4     // Card chip select pin
// DREQ should be an Int pin, see http://arduino.cc/en/Reference/attachInterrupt
#define DREQ 3       // VS1053 Data request, ideally an Interrupt pin

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
int myCanId = 0x20;
long loopIndexMax = 30000;
long sendEveryXLoops = 10000; //tied to loopIndexMax
int deviceType = 3;
bool isAlarmed = false;
const int BROADCAST_ADDR = 0x00;
const int DELAY_LOOP_TIME = 50;
MCP2515::ERROR canMessageError;
long loopIndex = 0;
int currentStatus = 0x00;

bool haventStarted = true;

Adafruit_VS1053_FilePlayer musicPlayer = Adafruit_VS1053_FilePlayer(SHIELD_RESET, SHIELD_CS, SHIELD_DCS, DREQ, CARDCS);
  
void setup() {
  Serial.begin(115200);
//  mcp2515.reset();
//  mcp2515.setBitrate(CAN_125KBPS);
//  mcp2515.setNormalMode();

  if (! musicPlayer.begin()) { // initialise the music player
     Serial.println(F("Couldn't find VS1053, do you have the right pins defined?"));
     while (1);
  }
  Serial.println(F("VS1053 found {Serial}"));
  
  if (!SD.begin(CARDCS)) {
    Serial.println(F("SD failed, or not present"));
    while (1);  // don't do anything more
  }

  // list files
  printDirectory(SD.open("/"), 0);
  
  // Set volume for left, right channels. lower numbers == louder volume!
  musicPlayer.setVolume(20,20);

  // Timer interrupts are not suggested, better to use DREQ interrupt!
  //musicPlayer.useInterrupt(VS1053_FILEPLAYER_TIMER0_INT); // timer int

  // If DREQ is on an interrupt pin (on uno, #2 or #3) we can do background
  // audio playing
  musicPlayer.useInterrupt(VS1053_FILEPLAYER_PIN_INT);  // DREQ int
  
  // Play one file, don't return until complete
  Serial.println(F("Playing condemn the hive"));
  musicPlayer.playFullFile("/CONDEMN.MP3");
  //musicPlayer.playFullFile("/GO.MP3");
  //musicPlayer.playFullFile("/WAKEUP.MP3");

  // Play another file in the background, REQUIRES interrupts!
  //Serial.println(F("Playing track 002"));
  //musicPlayer.startPlayingFile("/track002.mp3");
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
    if (incomingCanMsg.can_id == 0x14 && (incomingCanMsg.data[0] == 0x00 || incomingCanMsg.data[0] == myCanId)) { //if home base addresses to me/broadcasts a reset trip signal, stand down
      if (incomingCanMsg.data[1] == 0xBB) {
        isAlarmed = true;    
        currentStatus = 0xBB;
        

      } else if (incomingCanMsg.data[1] == 0xCC) {
        isAlarmed = false;
        currentStatus = 0x00;
        musicPlayer.stopPlaying();
      }
    }
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

  } else {
    if (debug && !suppressErrorDebugText) {
      Serial.print("ERROR READING CAN: ");
      Serial.println(ERROR_NAMES[canMessageError]);
    }
  }
  playMusic();

  if (haventStarted) {
        
        //musicPlayer.startPlayingFile("/CONDEMN.MP3");
        haventStarted = false;
  }
  
  if (loopIndex < loopIndexMax-1) loopIndex++;
  else loopIndex = 0;
  
  if (debug && loopIndex % sendEveryXLoops == 0) {Serial.print("loopIndex "); Serial.println(loopIndex);}
}


void playMusic() {
  if (isAlarmed) {
    musicPlayer.startPlayingFile("/CONDEMN.MP3");
  }
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

//void loop() {
//  // File is playing in the background
//  if (musicPlayer.stopped()) {
//    Serial.println("Done playing music");
//    while (1) {
//      delay(10);  // we're done! do nothing...
//    }
//  }
//  if (Serial.available()) {
//    char c = Serial.read();
//    
//    // if we get an 's' on the serial console, stop!
//    if (c == 's') {
//      musicPlayer.stopPlaying();
//    }
//    
//    // if we get an 'p' on the serial console, pause/unpause!
//    if (c == 'p') {
//      if (! musicPlayer.paused()) {
//        Serial.println("Paused");
//        musicPlayer.pausePlaying(true);
//      } else { 
//        Serial.println("Resumed");
//        musicPlayer.pausePlaying(false);
//      }
//    }
//  }
//
//  delay(100);
//}


/// File listing helper
void printDirectory(File dir, int numTabs) {
   while(true) {
     
     File entry =  dir.openNextFile();
     if (! entry) {
       // no more files
       //Serial.println("**nomorefiles**");
       break;
     }
     for (uint8_t i=0; i<numTabs; i++) {
       Serial.print('\t');
     }
     Serial.print(entry.name());
     if (entry.isDirectory()) {
       Serial.println("/");
       printDirectory(entry, numTabs+1);
     } else {
       // files have sizes, directories do not
       Serial.print("\t\t");
       Serial.println(entry.size(), DEC);
     }
     entry.close();
   }
}
