#include <SPI.h>
#include <mcp2515.h>

const bool debugOutput = false;
const long toneInterval = 50;	 // Interval between frequency changes (ms)
const int localBuzzerPin = 3;	 // d3=3 has pwm
const int loopIndexMax = 30000;	 // Loop index max for buzzer tone
int loopIndex = 0;				 // Loop index for buzzer tone
int loopDeviceIndex = 0;
bool enableLocalBuzzer = true;
bool localBuzzerSounding = false;
long previousMillis = 0;				// Tracks the last tone update
bool localBuzzerToneIncreasing = true;	// Direction of frequency sweep
int localBuzzerFrequency = 500;			// Current frequency

struct can_frame myCanMessage;
MCP2515 mcp2515(10);
MCP2515::ERROR canMessageError;

const int BROADCAST_ADDR = 0x00;
const int HOME_BASE_CAN_ID = 0x14;
const int SENSOR_TRIGGERED = 0xAA;
const int SENSOR_OK = 0x00;
const int SENSOR_OFF = 0xFF;
const int COMMAND_ENABLE_DEVICE = 0x0F;
const int COMMAND_DISABLE_DEVICE = 0x01;
const int COMMAND_TURN_ON_ALARM = 0xBB;
const int COMMAND_TURN_OFF_ALARM = 0xCC;
const int COMMAND_ENABLE_MOMENTARY_SWITCH = 0x0D;
const int ALARM_STATUS_OK = 0x00;
const int ALARM_STATUS_TRIGGERED = 0xBB;
const int MOMENTARY_SWITCH_STATUS_OK = 0x00;
const int MOMENTARY_SWITCH_TIMEOUT_MS = 500;

enum TYPE {
	MOMENTARY_SWITCH = 1,  // garage door opener, etc
	SENSOR = 2,			   // PIR, door open sensor, etc
	ALARM = 3			   // sound, visual, etc
};

struct Device {
	const TYPE type;				// config
	const int myCanId;				// config
	const int deviceType;			// config. per DeviceType[]
	const int ioPin;				// config. sensor: pin is connected to ground via resistor for a LOW signal (alarm at rest) or chain broken for a HIGH signal (alarm triggered) | alarm: LOW=off, should be connected to an analog pin for sweeping the buzzer.
	const int relayPin;				// config. -1 for no relay
	int sensorVal;					// state. for sensors only
	bool isAlarmed;					// state. for alarms only
	long nextStateChangeTimestamp;	// state. for momentary switches only - the hold time of the HIGH signal to the relay.
	bool isEnabled;					// state. this is the enable state for sensor devices that affects the relay state downstream, if any
	bool buzzerDirection;			// state. for alarms only. true = up, false = down in frequency
};

String DeviceType[] = {
	"",
	"controller",
	"motion sensor",
	"sound alarm",
	"visual alarm",
	"door open sensor",
	"momentary switch",	 // garage door opener
};

// initially don't enable too many/any devices that draw current, like PIRs - the inrush current could be too great
Device devices[] = {
	{
		type : SENSOR,
		myCanId : 0x31, /*garage side door*/
		deviceType : 5,
		ioPin : 5,
		relayPin : -1,	 /* -1 = no relay; writing LOW to this turns relay ON on a sensor */
		sensorVal : LOW, /* variable to store the sensor status (value) */
		isAlarmed : false,
		nextStateChangeTimestamp : 0,
		isEnabled : true, /* false = off; true = on; has direct effect on relay state if relay present */
		buzzerDirection : false
	},
	{
		type : SENSOR,
		myCanId : 0x50, /*front of house*/
		deviceType : 5,
		ioPin : 6,
		relayPin : -1,	 /* -1 = no relay; writing LOW to this turns relay ON on a sensor */
		sensorVal : LOW, /* variable to store the sensor status (value) */
		isAlarmed : false,
		nextStateChangeTimestamp : 0,
		isEnabled : true, /* false = off; true = on; has direct effect on relay state if relay present */
		buzzerDirection : false
	},
	{
		type : SENSOR,
		myCanId : 0x40, /*back door kitchen*/
		deviceType : 5,
		ioPin : 4,
		relayPin : -1,	 /* -1 = no relay; writing LOW to this turns relay ON on a sensor */
		sensorVal : LOW, /* variable to store the sensor status (value) */
		isAlarmed : false,
		nextStateChangeTimestamp : 0,
		isEnabled : true, /* false = off; true = on; has direct effect on relay state if relay present */
		buzzerDirection : false
	}};

const int numDevices = sizeof(devices) / sizeof(devices[0]); /* num connected devices */

struct can_frame incomingCanMsg;
String ERROR_NAMES[] = {"OK", "FAIL", "ALLTXBUSY", "FAILINIT", "FAILTX", "NOMSG"};
long lastSentMillis = 0;
int sendEveryMillis = 1000 / numDevices;

/// MSG DLC: 3 constant in all messages
/// MSG FORMAT: [0] TO (1 byte, number = specific ID OR 00 = broadcast)
///             [1] MSG (1 byte)
///             [2] DEVICETYPE (1 byte)
/// SENSOR MESSAGE DICTIONARY (00 - enabled and status ok, AA - enabled and status alarmed, BB - trigger alarm device, CC - reset alarm, FF - disabled)

// enum ERROR {
//     ERROR_OK        = 0,
//     ERROR_FAIL      = 1,
//     ERROR_ALLTXBUSY = 2,
//     ERROR_FAILINIT  = 3,
//     ERROR_FAILTX    = 4,
//     ERROR_NOMSG     = 5
// }

void setDigitalPinIfExists(int pin, int value) {
	if (pin == -1) {
		return -1;
	} else if (value != LOW && value != HIGH) {
		return -2;
	}

	digitalWrite(pin, value);
}

void setPinModeIfExists(int pin, int mode) {
	if (pin == -1) {
		return -1;
	} else if (mode != INPUT_PULLUP && mode != OUTPUT) {
		return -2;
	}

	pinMode(pin, mode);
}

void setup() {
	while (!Serial);

	Serial.begin(115200);

	mcp2515.reset();
	mcp2515.setBitrate(CAN_125KBPS);
	mcp2515.setNormalMode();

	pinMode(localBuzzerPin, OUTPUT);  // Set buzzer pin as output

	// initialize the device pins (inputs and relay, if applicable)
	for (int i = 0; i < numDevices; i++) {
		if (devices[i].type == SENSOR) {
			pinMode(devices[i].ioPin, INPUT_PULLUP);  // initialize sensor as an input
			setPinModeIfExists(devices[i].relayPin, OUTPUT);
			setDigitalPinIfExists(devices[i].relayPin, devices[i].isEnabled ? LOW : HIGH);	// low = on, high = off
		} else if (devices[i].type == ALARM) {
			//no setup for ioPin, it is a variable output, analog pin
			setPinModeIfExists(devices[i].relayPin, OUTPUT);
			setDigitalPinIfExists(devices[i].relayPin, LOW);  // low = off
		} else if (devices[i].type == MOMENTARY_SWITCH) {
			setPinModeIfExists(devices[i].ioPin, OUTPUT);
			setDigitalPinIfExists(devices[i].ioPin, LOW);  // low = off
			setPinModeIfExists(devices[i].relayPin, OUTPUT);
			setDigitalPinIfExists(devices[i].relayPin, LOW);  // low = off
		}

		/* set up those parts of the outgoing CAN message that don't change */
		myCanMessage.can_dlc = 3;
		myCanMessage.data[0] = HOME_BASE_CAN_ID;
		myCanMessage.data[1] = 0x00;  // nothing
		myCanMessage.data[2] = 0x00;  // nothing

		delay(100);	 // wait for relays to init (actually click into place) to avoid false alarms
	}
}

// for SENSOR type devices only
void setSensorEnableState(int deviceNumber, bool newState) {
	if (newState == true && devices[deviceNumber].isEnabled == false ||	 //if toggling from current state
		newState == false && devices[deviceNumber].isEnabled == true) {
		devices[deviceNumber].isEnabled = newState;
		setDigitalPinIfExists(devices[deviceNumber].relayPin, newState ? LOW : HIGH);  // low = on
		if (debugOutput && devices[deviceNumber].relayPin != -1) {
			Serial.println(String(">>>>>>>>>>>") + String(newState ? "EN" : "DIS") + String("ABLING RELAY>>>>>>>>>>>"));
		}

		delay(100);	 // delay sending anything while the sensor gets power and begins reading an OK value while powering up
	}
}

void makeMessage(int deviceNumber, int message) {
	myCanMessage.can_id = devices[deviceNumber].myCanId;
	myCanMessage.data[0] = HOME_BASE_CAN_ID;
	myCanMessage.data[2] = devices[deviceNumber].deviceType;

	if (devices[deviceNumber].type == SENSOR) {
		if (devices[deviceNumber].isEnabled == true && devices[deviceNumber].sensorVal == HIGH) {
			myCanMessage.data[1] = SENSOR_TRIGGERED;  // alarm
		} else if (devices[deviceNumber].isEnabled == true && devices[deviceNumber].sensorVal == LOW) {
			myCanMessage.data[1] = SENSOR_OK;  // ok
		} else if (devices[deviceNumber].isEnabled == false) {
			myCanMessage.data[1] = SENSOR_OFF;	// off
		}
	} else if (devices[deviceNumber].type == ALARM) {
		if (devices[deviceNumber].isAlarmed) {
			myCanMessage.data[1] = ALARM_STATUS_TRIGGERED;	// alarm
		} else {
			myCanMessage.data[1] = ALARM_STATUS_OK;	 // ok
		}

	} else if (devices[deviceNumber].type == MOMENTARY_SWITCH) {
		myCanMessage.data[1] = MOMENTARY_SWITCH_STATUS_OK;	// ok
	}
}

void sendMessage(int deviceNumber, int message) {
	makeMessage(deviceNumber, message);
	mcp2515.sendMessage(&myCanMessage);

	if (debugOutput) {
		Serial.print(myCanMessage.data[1], HEX);

		Serial.print(" sent to 0x");
		Serial.print(myCanMessage.data[0], HEX);
		Serial.print(" from 0x");
		Serial.print(devices[deviceNumber].myCanId, HEX);
		if (devices[deviceNumber].deviceType >= 0 && devices[deviceNumber].deviceType < sizeof(DeviceType) / sizeof(DeviceType[0])) {  //sanity check for out of bounds incoming device type over CAN bus
			Serial.print(" : ");
			Serial.println(DeviceType[devices[deviceNumber].deviceType]);
		}
	}
}

bool readIncomingCanMessage() {
	canMessageError = mcp2515.readMessage(&incomingCanMsg);
	if (canMessageError == MCP2515::ERROR_OK) {
		if (incomingCanMsg.can_id == HOME_BASE_CAN_ID) {
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
int matchMessageToThisDevice() {
	if (incomingCanMsg.can_id == HOME_BASE_CAN_ID)	// received message coming from home base
	{
		if (incomingCanMsg.data[0] == BROADCAST_ADDR)  // received message has recipient listed as BROADCAST
		{
			return -1000;  // broadcast
		}
		for (int i = 0; i < numDevices; i++) {
			if (incomingCanMsg.data[0] == devices[i].myCanId) {	 // received message has recipient specified as one of the devices in "devices"
				return i;										 // device array index in devices
			}
		}
	}
	return -1;	// unmatched~no such device
}

void processIncomingCanMessage() {
	int deviceNum = matchMessageToThisDevice();
	String debugMessage;

	if (deviceNum == -1) {
		debugMessage = ">>>>>>>>>>>MESSAGE NOT MATCHED TO ANY DEVICE>>>>>>>>>>>";
	} else if (deviceNum == -1000) {
		debugMessage = ">>>>>>>>>>>MESSAGE MATCHED TO ALL DEVICES>>>>>>>>>>>";
		for (int i = 0; i < numDevices; i++) {
			setStateAccordingToMessage(i);
		}
	} else {
		debugMessage = ">>>>>>>>>>>MESSAGE MATCHED TO DEVICE " + String(devices[deviceNum].myCanId, HEX) + ">>>>>>>>>>>";
		setStateAccordingToMessage(deviceNum);
	}

	if (debugOutput) {
		Serial.println(debugMessage);
		debugPrintIncoming();
	}
}

void setStateAccordingToMessage(int deviceNum) {
	bool newState;	//true = enabled; false = disabled

	if (devices[deviceNum].type == SENSOR) {
		if (incomingCanMsg.data[1] == COMMAND_ENABLE_DEVICE) {	// enable
			newState = true;
		} else if (incomingCanMsg.data[1] == COMMAND_DISABLE_DEVICE) {	// disable
			newState = false;
		}
		setSensorEnableState(deviceNum, newState);
	} else if (devices[deviceNum].type == ALARM) {
		if (incomingCanMsg.data[1] == COMMAND_TURN_ON_ALARM) {
			devices[deviceNum].isAlarmed = true;
		} else if (incomingCanMsg.data[1] == COMMAND_TURN_OFF_ALARM) {
			devices[deviceNum].isAlarmed = false;
		}
	} else if (devices[deviceNum].type == MOMENTARY_SWITCH) {
		if (incomingCanMsg.data[1] == COMMAND_ENABLE_MOMENTARY_SWITCH) {
			setDigitalPinIfExists(devices[deviceNum].ioPin, HIGH);
			setDigitalPinIfExists(devices[deviceNum].relayPin, HIGH);
			devices[deviceNum].nextStateChangeTimestamp = millis() + MOMENTARY_SWITCH_TIMEOUT_MS;
		}
	}
}

void loop() /* go through all devices: read incoming CAN message, send message for each device when appropriate */
{
	if (readIncomingCanMessage()) {
		processIncomingCanMessage();
	}

	long now = millis();

	if (enableLocalBuzzer) localBuzzerSounding = false;

	for (int i = 0; i < numDevices; i++) {
		if (devices[i].type == SENSOR) {
			devices[i].sensorVal = digitalRead(devices[i].ioPin); /*LOW by default, no motion detected*/
			if (enableLocalBuzzer) {
				localBuzzerSounding = localBuzzerSounding || (devices[i].sensorVal == HIGH && devices[i].isEnabled == true);
			}
		} else if (devices[i].type == ALARM) {
			setAlarmBuzzerToneState(i);
			setDigitalPinIfExists(devices[i].relayPin, devices[i].isAlarmed ? HIGH : LOW);

		} else if (devices[i].type == MOMENTARY_SWITCH) {
			//if it's time to switch off the momentary switch after the hold timeout, do so
			if (devices[i].nextStateChangeTimestamp != 0 && now > devices[i].nextStateChangeTimestamp) {
				setDigitalPinIfExists(devices[i].ioPin, LOW);
				setDigitalPinIfExists(devices[i].relayPin, LOW);
				devices[i].nextStateChangeTimestamp = 0;
			}
		}
	}

	//Buzzer tone things
	if (loopIndex < loopIndexMax - 1)
		loopIndex++;
	else
		loopIndex = 0;

	if (enableLocalBuzzer && localBuzzerSounding && now - previousMillis >= toneInterval) {
		previousMillis = now;  // Update the time

		// Play the tone at the current frequency
		tone(localBuzzerPin, localBuzzerFrequency);

		// Update the frequency. Up by 10 if increasing until 2000, down by 10 if decreasing until 500.
		localBuzzerFrequency += 10 * (localBuzzerToneIncreasing ? 1 : -1);
		if (localBuzzerFrequency >= 2000 || localBuzzerFrequency <= 500) {
			localBuzzerToneIncreasing = !localBuzzerToneIncreasing;
		}
	} else if (enableLocalBuzzer && !localBuzzerSounding) {
		noTone(localBuzzerPin);
	}

	if ((now > lastSentMillis + sendEveryMillis) || now < lastSentMillis && now > sendEveryMillis) {  // only send a message if it's been "sendEveryMillis" OR the timer has cycled around LONG
		sendMessage(loopDeviceIndex, 0);
		lastSentMillis = now;
		if (loopDeviceIndex == numDevices - 1) {
			loopDeviceIndex = 0;
		} else {
			loopDeviceIndex++;
		}
	}
}

void setAlarmBuzzerToneState(int deviceIndex) {
	if (deviceIndex < 0 || deviceIndex >= numDevices || devices[deviceIndex].ioPin == -1) {
		return;
	}

	if (devices[deviceIndex].isAlarmed) {
		int factor = 3000;
		int freqConstant = 500;
		if (loopIndex % factor == 0) {
			devices[deviceIndex].buzzerDirection = !devices[deviceIndex].buzzerDirection;
		}

		int alarmBuzzerFrequency;

		if (devices[deviceIndex].buzzerDirection)
			alarmBuzzerFrequency = freqConstant + loopIndex % factor;
		else
			alarmBuzzerFrequency = freqConstant + factor - loopIndex % factor;
		tone(devices[deviceIndex].ioPin, alarmBuzzerFrequency, 5);
	} else {
		noTone(devices[deviceIndex].ioPin);
	}
}

//Print the incoming CANBUS message to Serial if debugOutput is set to true
void debugPrintIncoming() {
	if (!debugOutput) {
		return;
	}

	String output = "\n\n>>>INCOMING MESSAGE\nSENDER CAN ID: " + String(incomingCanMsg.can_id, HEX) + " LENGTH: " + String(incomingCanMsg.can_dlc, HEX) + "\n";
	for (int i = 0; i < incomingCanMsg.can_dlc; i++) {	// print the data
		output = output + " byte " + i + ": " + String(incomingCanMsg.data[i], HEX);
	}
	output += "\n";
	Serial.println(output);
}
