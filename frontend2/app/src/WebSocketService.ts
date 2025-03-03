import * as Comlink from "comlink";
import { ComWorkerAPI } from "@/app/workers/ComWorker";
import { setStatus, setPastEvents, setAlarmProfiles, setIsConnected, setIsError, setIsLoaded } from "@components/AppStateSlice";

let comAPI: Comlink.Remote<ComWorkerAPI> | null = null;
let lastClickTime: EpochTimeStamp = 0;
const timeout: number = 2500;

export const initializeWebSocket = (dispatch: (action: any) => void) => {
  const worker = new Worker(new URL("@workers/ComWorker.ts", import.meta.url));
  comAPI = Comlink.wrap(worker);
  let firstLoad = true;

  let getPastEventsTimeout: undefined | NodeJS.Timeout = undefined;

  const statusHandler = (message: object): void => {
	dispatch(setStatus(message));
	
	if (getPastEventsTimeout) { clearTimeout(getPastEventsTimeout); }
	getPastEventsTimeout = setTimeout(() => {
		dispatch(setIsLoaded(true));
		comAPI?.emitEvent('getPastEvents', { message: undefined });
	  if (getPastEventsTimeout) clearTimeout(getPastEventsTimeout);
	  firstLoad = false;
	}, firstLoad ? 1 : 3000);
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
		if (lastClickTime > Date.now() - timeout) return; //don't allow clicks that are frequent
		lastClickTime = Date.now();
		comAPI.emitEvent('arm', {message: undefined});
	}
};

export const emitArmAndChangeProfileEvent = (profileId: number, isArmed: boolean) => {
	emitChangeProfileEvent(profileId);
		
	if (!isArmed) {
		setTimeout(()=>{
			comAPI?.emitEvent('arm', {message: undefined});
		}, 1000);
	}
};

export const emitChangeProfileEvent = (profileId: number) => {
	if (comAPI) {
		if (lastClickTime > Date.now() - timeout) return; //don't allow clicks that are frequent
		lastClickTime = Date.now();

		comAPI.emitEvent('setAlarmProfile', {message: profileId});		
	}
};

export const emitDisarmEvent = () => {
	if (comAPI) {
		if (lastClickTime > Date.now() - timeout) return; //don't allow clicks that are frequent
		lastClickTime = Date.now();
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