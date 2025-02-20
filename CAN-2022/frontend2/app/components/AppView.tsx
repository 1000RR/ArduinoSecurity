"use client";

import TopPanel from "@components/TopPanel";
import IndicatorPanel from "@components/IndicatorPanel";
import ButtonWithDrawer from "@components/ButtonWithDrawer";
import GarageDoorButton from "@/app/components/GarageDoorButton";
import UnavailableOverlay from "@components/UnavailableOverlay";
import Image from "next/image";

import { useEffect } from "react";
import { useSelector, useDispatch } from 'react-redux';
import { AppState } from "./AppStateSlice";
import { initializeWebSocket } from "@components/WebSocketService";

const AppView: React.FC = () => {
    const appState: AppState = useSelector((state: object) => state.appState); //appState is the name of the slice
    const dispatch = useDispatch();

    useEffect(() => {
        const terminateWebSocket = initializeWebSocket(dispatch);

        return () => {
            terminateWebSocket();
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