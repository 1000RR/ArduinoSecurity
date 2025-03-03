import { configureStore } from '@reduxjs/toolkit';
import { AppStateSlice } from '@components/AppStateSlice';

export default configureStore({
  reducer: {
    appState: AppStateSlice.reducer
  },
})