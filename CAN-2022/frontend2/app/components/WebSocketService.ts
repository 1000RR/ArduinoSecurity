// filepath: /Users/uzun/Development/Arduino Projects/ArduinoSecurity/CAN-2022/frontend2/app/components/webSocketService.ts
import * as Comlink from "comlink";
import { ComWorkerAPI } from "@/app/workers/ComWorker";
import { setStatus, setPastEvents, setAlarmProfiles, setIsConnected, setIsError, setIsLoaded } from "./AppStateSlice";

let comAPI: Comlink.Remote<ComWorkerAPI> | null = null;

export const initializeWebSocket = (dispatch: (action: any) => void) => {
  const worker = new Worker(new URL("@workers/ComWorker.ts", import.meta.url));
  comAPI = Comlink.wrap(worker);

  let getPastEventsTimeout: undefined | NodeJS.Timeout = undefined;

  const statusHandler = (message: object): void => {
	dispatch(setStatus(message));
	
	if (getPastEventsTimeout) { clearTimeout(getPastEventsTimeout); }
	getPastEventsTimeout = setTimeout(() => {
		dispatch(setIsLoaded(true));
		comAPI?.emitEvent('getPastEvents', { message: undefined });
	  if (getPastEventsTimeout) clearTimeout(getPastEventsTimeout);
	}, 3000);
  };

  const pastEventsHandler = (message: object): void => {
	dispatch(setPastEvents(message));
  };

  const alarmProfilesHandler = (message: object): void => {
	dispatch(setAlarmProfiles(message));
  };

  const handlerMappings: Record<string, (data: object) => void> = {
	'postStatus': statusHandler,
	'postPastEvents': pastEventsHandler,
	'postAlarmProfiles': alarmProfilesHandler
  };

  const socketIOErrorHandler = (error: Error): void => {
	dispatch(setIsError(true));
	dispatch(setIsConnected(false));
	dispatch(setIsLoaded(false));
  };

  const socketIOMessageHandler = (message: { data: { message: object }, eventName: string }): void => {
	dispatch(setIsError(false));

	if (message.eventName in handlerMappings) {
	  handlerMappings[message.eventName](message.data.message);
	}
  };

  const socketIOConnectHandler = (): void => {
	dispatch(setIsConnected(true));
  };

  comAPI.setupWebSockets(
	Object.keys(handlerMappings),
	Comlink.proxy(socketIOMessageHandler),
	Comlink.proxy(socketIOErrorHandler),
	Comlink.proxy(socketIOConnectHandler)
  );

  return () => {
	worker.terminate();
  };
};

export const emitGarageDoorToggleEvent = () => {
  if (comAPI) {
	comAPI.emitEvent('toggleGarageDoorState', {message: undefined});
  }
};

export const emitArmEvent = () => {
	if (comAPI) {
		comAPI.emitEvent('arm', {message: undefined});
	}
};

export const emitArmAndChangeProfileEvent = (profileId: number) => {
	if (comAPI) {
		comAPI.emitEvent('setAlarmProfile', {message: profileId})
		setTimeout(()=>{
			comAPI?.emitEvent('arm', {message: undefined});
		}, 2000)
	}
};

export const emitDisarmEvent = () => {
	if (comAPI) {
		comAPI.emitEvent('disarm', {message: undefined});
	}
};

export const emitGetAttentionEvent = () => {
	if (comAPI) {
		comAPI.emitEvent('checkPhones', {message: undefined});
	}
};

export const emitTestAlarmEvent = () => {
	if (comAPI) {
		comAPI.emitEvent('alarmSoundOn', {message: undefined});
	}
};

export const emitClearDataEvent = () => {
	if (comAPI) {
		comAPI.emitEvent('clearOldData', {message: undefined});
	}
};

export const emitSendSpecialOnce = (message: string) => {
	if (comAPI) {
		comAPI.emitEvent('cansendsingle', {message: message});
	}
};

export const emitSendSpecialRepeatedly = (message: string) => {
	if (comAPI) {
		comAPI.emitEvent('cansendrepeatedly', {message: message});
	}
};

export const emitStopSendingSpecial = () => {
	if (comAPI) {
		comAPI.emitEvent('canstopsending', {message: undefined});
	}
};





