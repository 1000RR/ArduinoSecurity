import { createSlice } from '@reduxjs/toolkit'

export type PastEvent = {
    event: string;
    time: string;
    trigger?: string;
    method?: string;
}
  
export type PastEventsResponse = {
    pastEvents: PastEvent[];
}

export type AlarmProfile = {
    index: number;
    name: string;
    sensorsThatTriggerAlarm?: string[];
    missingDevicesThatTriggerAlarm?: string[];
    alarmOutputDevices?: string[];
    alarmTimeLengthSec: number;
    playSound?: string;
    playSoundVolume?: number;
}

export type AlarmProfilesResponse = {
    profiles: AlarmProfile[];
};

export type StatusResponse = {
    armStatus: string;
    alarmStatus: string;
    garageOpen: boolean;
    profile: string;
    profileNumber: string;
    currentTriggeredDevices: string[];
    currentMissingDevices: string[];
    everTriggeredWithinAlarmCycle: string[];
    everTriggeredWithinArmCycle: string[];
    everMissingWithinArmCycle: string[];
    everMissingDevices: string[];
    memberCount: number;
    memberDevices: string[];
    memberDevicesReadable: string[];
}

export interface AppState {
    status: string | StatusResponse;
    pastEvents: string | PastEventsResponse;
    alarmProfiles: string | AlarmProfilesResponse;
    isConnected: boolean;
    isError: boolean;
}

const initialState: AppState = {
  status: "not yet loaded",
  pastEvents: "not yet loaded",
  alarmProfiles: "not yet loaded",
  isConnected: false,
  isError: false
};

export const AppStateSlice = createSlice({
  name: 'appState',
  initialState: initialState,
  reducers: {
    setStatus: (state, action) => {
      state.status = action.payload
    },
    setPastEvents: (state, action) => {
        state.pastEvents = action.payload
    },
    setAlarmProfiles: (state, action) => {
        state.alarmProfiles = action.payload
    },
    setIsConnected: (state, action) => {
        state.isConnected = action.payload
    },
    setIsError: (state, action) => {
      state.isError = action.payload
  }
  },
})

// Action creators are generated for each case reducer function
export const { setStatus, setPastEvents, setAlarmProfiles, setIsConnected, setIsError } = AppStateSlice.actions

export default AppStateSlice.reducer