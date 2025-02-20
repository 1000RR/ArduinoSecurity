"use client";

import TopPanel from "@components/TopPanel";
import IndicatorPanel from "@components/IndicatorPanel";
import ButtonWithDrawer from "@components/ButtonWithDrawer";
import GarageDoorButton from "@/app/components/GarageDoorButton";
import UnavailableOverlay from "@components/UnavailableOverlay";
import Image from "next/image";

import { useEffect } from "react";
import { useSelector, useDispatch } from 'react-redux';
import { AppState, setStatus, setIsConnected, setPastEvents, setAlarmProfiles, setIsError } from "./AppStateSlice";

import * as Comlink from "comlink";
import { ComWorkerAPI } from "@/app/workers/ComWorker";

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

const AppView: React.FC = () => {
    const appState: AppState = useSelector((state: object) => state.appState); //appState is the name of the slice
    const dispatch = useDispatch();

    useEffect(() => {
        const worker = new Worker(new URL("@workers/ComWorker.ts", import.meta.url));
        const ComAPI = Comlink.wrap(worker);
        
        let getPastEventsTimeout: undefined | NodeJS.Timeout = undefined;

        const statusHandler = (message: object): void => {
            console.log(`GOT STATUS ${JSON.stringify(message)}`);

            dispatch(setStatus(message));
            
            if (getPastEventsTimeout) {clearTimeout(getPastEventsTimeout)};
            getPastEventsTimeout = setTimeout(()=>{
                (ComAPI as Comlink.Remote<ComWorkerAPI>).emitEvent(
                    'getPastEvents', 
                    { message: undefined }
                );
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

        // eslint-disable-next-line no-unused-vars
        const handlerMappings: Record<string, (data: object) => void> = {
            'postStatus': statusHandler, 
            'postPastEvents': pastEventsHandler, 
            'postAlarmProfiles': alarmProfilesHandler
        };
    
        // eslint-disable-next-line no-unused-vars, @typescript-eslint/no-unused-vars
        const socketIOErrorHandler = (error: Error): void => {
            dispatch(setIsError(true));
            dispatch(setIsConnected(false));
        };

        const socketIOMessageHandler = (message: SocketIOMessage): void => {
            console.log(`||||| SOCKETIO: received ${message.eventName} |||||`);

            dispatch(setIsError(false));

            if (message.eventName in handlerMappings) {
                handlerMappings[message.eventName](message.data.message);
            }
        };

        const socketIOConnectHandler = (): void => {
            dispatch(setIsConnected(true));
        };

        (ComAPI as Comlink.Remote<ComWorkerAPI>).setupWebSockets(
            Object.keys(handlerMappings),
            Comlink.proxy(socketIOMessageHandler),
            Comlink.proxy(socketIOErrorHandler),
            Comlink.proxy(socketIOConnectHandler)
        );

        return () => {
                worker.terminate();
        };
    }, [dispatch]);
    
    const serviceAvailable = appState.isConnected && !appState.error;
    const unavailableContent = <div style={{display: "flex", flexDirection: "column", alignItems: "center"}}>
            Service Unavailable
            <Image className="fadeoutImageRound" src={"/assets/dogsleep.jpg"} width="150" height="150" alt=""></Image>
        </div>;
    const loadingContent = <div style={{display: "flex", flexDirection: "column", alignItems: "center"}}>
        Loading...
    </div>;

    return (
        <>
            { serviceAvailable ? 
                <div>
                    <TopPanel></TopPanel>
                    <IndicatorPanel></IndicatorPanel>
                    <ButtonWithDrawer flexDirection="row" buttonText="Garage Door">
                        <GarageDoorButton></GarageDoorButton>
                    </ButtonWithDrawer>
                    <ButtonWithDrawer flexDirection="column" buttonText="Quick Arm / Disarm"></ButtonWithDrawer>
                    <ButtonWithDrawer flexDirection="column" buttonText="Special Functions"></ButtonWithDrawer>
                    <ButtonWithDrawer flexDirection="row" justifyContent="flex-start" buttonText="Status"><pre>{JSON.stringify(appState.status, null, 2)}</pre></ButtonWithDrawer>
                    <ButtonWithDrawer flexDirection="row" justifyContent="flex-start" buttonText="Past Events"><pre>{JSON.stringify(appState.pastEvents, null, 2)}</pre></ButtonWithDrawer>
                    <ButtonWithDrawer flexDirection="row" justifyContent="flex-start" buttonText="Profiles"><pre>{JSON.stringify(appState.alarmProfiles, null, 2)}</pre></ButtonWithDrawer>
                </div> :
                <div>
                    <UnavailableOverlay>{appState.isError ? unavailableContent : loadingContent}</UnavailableOverlay>
                </div>
            }
        </>
    );
};

export default AppView;