// filepath: /Users/uzun/Development/Arduino Projects/ArduinoSecurity/CAN-2022/frontend2/app/components/webSocketService.ts
import * as Comlink from "comlink";
import { ComWorkerAPI } from "@/app/workers/ComWorker";
import { setStatus, setPastEvents, setAlarmProfiles, setIsConnected, setIsError } from "./AppStateSlice";

let comAPI: Comlink.Remote<ComWorkerAPI> | null = null;

export const initializeWebSocket = (dispatch: (action: any) => void) => {
  const worker = new Worker(new URL("@workers/ComWorker.ts", import.meta.url));
  comAPI = Comlink.wrap(worker);

  let getPastEventsTimeout: undefined | NodeJS.Timeout = undefined;

  const statusHandler = (message: object): void => {
	console.log(`GOT STATUS ${JSON.stringify(message)}`);

	dispatch(setStatus(message));

	if (getPastEventsTimeout) { clearTimeout(getPastEventsTimeout); }
	getPastEventsTimeout = setTimeout(() => {
	  comAPI?.emitEvent('getPastEvents', { message: undefined });
	  if (getPastEventsTimeout) clearTimeout(getPastEventsTimeout);
	}, 3000);
  };

  const pastEventsHandler = (message: object): void => {
	console.log(`GOT PAST EVENTS ${JSON.stringify(message)}`);
	dispatch(setPastEvents(message));
  };

  const alarmProfilesHandler = (message: object): void => {
	console.log(`GOT ALARM PROFILES ${JSON.stringify(message)}`);
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
  };

  const socketIOMessageHandler = (message: { data: { message: object }, eventName: string }): void => {
	console.log(`||||| SOCKETIO: received ${message.eventName} |||||`);

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

export const emitDisarmEvent = () => {
	if (comAPI) {
		comAPI.emitEvent('disarm', {message: undefined});
	}
};