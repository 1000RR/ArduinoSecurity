import { createSlice } from '@reduxjs/toolkit';

interface AlarmStatus {
  isArmed: boolean;
  alarmTriggered: boolean;
}

const initialState: AlarmStatus = {
  isArmed: false,
  alarmTriggered: false,
};

const alarmStateSlice = createSlice({
  name: 'alarmStatus',
  initialState,
  reducers: {
    setState(state) {
      state.isArmed = true;
    }
  },
});

export const { setState } = alarmStateSlice.actions;
export default alarmStateSlice.reducer;