#!/bin/bash

VOL=$(($1-81)) #subtract 81 always - db scale conversion
wget -O /dev/null 192.168.2.191/MainZone/index.put.asp?cmd0=PutMasterVolumeSet%2F$VOL

