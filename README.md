
<img width="899" alt="bobik" src="https://github.com/user-attachments/assets/b32ab92e-6264-4e49-999e-a96790421e8a" />


## Idea
#### Let residents know if a trespassing event occurs at night
#### Let the neighbors know audibly that the home is being trespassed into when away
#### Control via WebUI over HTTPS&WSS gated by password (for some session length) or an on-client-device cert signed by an (intermediate) master cert. 

### Resilience
#### should be resilient to power outages (for a given amount of time), disconnection of devices on the CAN bus is treated as a security event (alarm trigger) for those devices explicitly being monitored.

### Remote functionality (via VPN)
#### Control any alarm functionality; get present residents' attention to their phones via audible alarm; control garage door and see its closed/opened status.


### Details to expand upon
- lots hard-coded
- 3 types of logical devices: sensors, alarms, momentary relay switches (for integrating into garage door, etc).
- Audio alarms: Denon (POST request-controlled over LAN), buzzer, fire alarm bell, piezo buzzer. High-current devices draw power directly from the bus, through a relay that is operated by a control Arduino board.
- Power backup: UPS for control unit; stabilized, normalized voltage marine battery constantly on a tender feeding the bus' Vsource with 12v.


TODO:
- support for Vsource line voltage monitoring and threshold warning in UI / email.
- support for UPS status monitoring and state change warning in UI / email.
- more past events log from memory to DB; DB should have a sweep job based on back date and/or number of events.
  - searching for events from UI.
- minimize hard coding. Load as much as possible from config files and/or DB.
- move access password from nginx.conf.
- control unit time and/or client time displayed in UI in local/GMT formats.
- front end security: implement CSP.
- install dependencies script should include pip dependencies (both on device at (re)install time and in dev env)
