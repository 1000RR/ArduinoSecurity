import * as Comlink from 'comlink';
import { io, Socket } from 'socket.io-client';
import {SocketIOMessage} from '@components/MainAppView';

export type ComWorkerAPI = {
	setupWebSockets(eventNames: Array<string>, handlerFunction: (data: SocketIOMessage) => void): void;
	emitEvent(eventName: string, data: object): void;
};

let socket: Socket | null = null;

const api: ComWorkerAPI = {
	setupWebSockets(eventNames, handlerFunction): void {
		socket = io('https://bobik.lan:8080');

		socket.on('connect', function() {
			console.log('Connected to server');
			socket?.emit('getAlarmProfiles', { message: undefined });
		});

		socket.on('connect_error', (err: Error) => handleErrors(err));
		
		socket.on('connect_failed', (err: Error) => handleErrors(err));

		function handleErrors(err: Error) {
			console.log('Websocket Error: ' + err);
			//call error handler
			setTimeout(() => {
				socket?.connect();
			}, 1000);
		};

		eventNames.forEach((eventName: string) => {
			socket?.on(eventName, (data: object): void => {handlerFunction({data: data, eventName: eventName})});
		});
	},
	emitEvent(eventName, data): void {
		socket?.emit(eventName, data);
	}
	// Add more functions as needed
};

// Expose the API to the main thread
Comlink.expose(api);