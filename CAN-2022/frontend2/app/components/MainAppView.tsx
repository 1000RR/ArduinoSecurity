"use client";

import TopPanel from "@components/TopPanel";
import IndicatorPanel from "@components/IndicatorPanel";
import ButtonWithDrawer from "@/app/components/ButtonWithDrawer";
import UnavailableOverlay from "@/app/components/UnavailableOverlay";
import { useEffect, useState } from "react";
import * as Comlink from "comlink";
import { ComWorkerAPI } from "@/app/workers/ComWorker";
import Image from "next/image";

export interface SocketIOMessage {
	data: {
		message: object;
	},
	eventName: string;
}

export interface SocketIOHandlerMessage {
	message: object;
	eventName: string;
}

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

const MainAppView: React.FC = () => {
		// eslint-disable-next-line @typescript-eslint/no-unused-vars, no-unused-vars
		const [state, setState] = useState<Record<string, number>>({ res: 0});
		
	useEffect(() => {
		const worker = new Worker(new URL("@workers/ComWorker.ts", import.meta.url));
		const ComAPI = Comlink.wrap(worker);

		let getPastEventsTimeout: undefined | NodeJS.Timeout = undefined;

		const statusHandler = (message: object): void => {
			console.log(`GOT STATUS ${JSON.stringify(message)}`);
			
			if (getPastEventsTimeout) {clearTimeout(getPastEventsTimeout)};
			getPastEventsTimeout = setTimeout(()=>{
				(ComAPI as Comlink.Remote<ComWorkerAPI>).emitEvent(
					'getPastEvents', 
					{ message: undefined }
				);
				if (getPastEventsTimeout) clearTimeout(getPastEventsTimeout);
			}, 3000);
		};
		const pastEventsHandler = (data: object): void => {
			console.log(`GOT PAST EVENTS ${JSON.stringify(data)}`);
		};
		const alarmProfilesHandler = (message: object): void => {
			console.log(`GOT ALARM PROFILES ${JSON.stringify(message)}`);
		};

			// eslint-disable-next-line no-unused-vars
			const handlerMappings: Record<string, (data: object) => void> = {
				'postStatus': statusHandler, 
				'postPastEvents': pastEventsHandler, 
				'postAlarmProfiles': alarmProfilesHandler
			};
		
			const socketIOMessageHandler = (message: SocketIOMessage): void => {
				console.log(`||||| SOCKETIO: received ${message.eventName} |||||`);

				if (message.eventName in handlerMappings) {
					handlerMappings[message.eventName](message.data.message);
				}
			};

			(ComAPI as Comlink.Remote<ComWorkerAPI>).setupWebSockets(
				Object.keys(handlerMappings),
				Comlink.proxy(socketIOMessageHandler)
			);

			return () => {
					worker.terminate();
			};
		}, []);

		const serviceAvailable = true;
		const overlayContents = <>
				Service Unavailable
				<Image className="fadeoutImageRound" src={"assets/dogsleep.jpg"} width="150" alt=""></Image>
			</>;
	
	return (<>
		{ !serviceAvailable && <UnavailableOverlay>{overlayContents}</UnavailableOverlay>}
		{ serviceAvailable && 
			<>
				<TopPanel></TopPanel>
				<IndicatorPanel></IndicatorPanel>
				<ButtonWithDrawer flexDirection="row" buttonText="Garage Door">
					<div>CNT {state.res}</div><div>RES {state.res} </div>
				</ButtonWithDrawer>
				<ButtonWithDrawer flexDirection="column" buttonText="Quick Arm / Disarm">
				<div>CNT {state.res}</div><div>RES {state.res} </div>
				</ButtonWithDrawer>
				<ButtonWithDrawer flexDirection="column" buttonText="Special Functions"></ButtonWithDrawer>
				<ButtonWithDrawer flexDirection="column" buttonText="Status"></ButtonWithDrawer>
				<ButtonWithDrawer flexDirection="column" buttonText="Past Events"></ButtonWithDrawer>
				<ButtonWithDrawer flexDirection="column" buttonText="Profiles"></ButtonWithDrawer>
			</>
		}
	 </>
	);
};

export default MainAppView;