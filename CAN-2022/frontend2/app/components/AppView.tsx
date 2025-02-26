"use client";

import TopPanel from "@components/TopPanel";
import IndicatorPanel from "@components/IndicatorPanel";
import ButtonWithDrawer from "@components/ButtonWithDrawer";
import GarageDoorButton from "@/app/components/GarageDoorButton";
import UnavailableOverlay from "@components/UnavailableOverlay";
import ArmButtonList from "@components/ArmButtonList";
import SpecialFunctions from "@components/SpecialFunctions";
import Image from "next/image";
import Button from "./Button";


import { useEffect } from "react";
import { useSelector, useDispatch } from 'react-redux';
import { AppState, AppStateSlice } from "./AppStateSlice";
import { initializeWebSocket } from "@src/WebSocketService";
import TopPanelSpacer from "./TopPanelSpacer";

const AppView: React.FC = () => {
    const appState: AppState = useSelector((state: AppStateSlice) => state.appState); //appState is the name of the slice
    const dispatch = useDispatch();

    useEffect(() => {
        const terminateWebSocket = initializeWebSocket(dispatch);

        return () => {
            terminateWebSocket();
        };
    }, [dispatch]);
    
    const serviceAvailable = appState.isConnected && !appState.isError && appState.isLoaded;
    const alarmTriggered = appState.status.alarmStatus === 'ALARM';
    const unavailableContent = <div style={{display: "flex", flexDirection: "column", alignItems: "center"}}>
            Service Unavailable
            <Image className="fadeoutImageRound" src={"/assets/dogsleep.jpg"} width="150" height="150" alt=""></Image>
        </div>;
    const loadingContent = <div style={{display: "flex", flexDirection: "column", alignItems: "center"}}>
        Loading
        <Image className="fadeoutImageRound" src={"/assets/dogread.jpg"} width="150" height="150" alt=""></Image>
    </div>;

    const scrollToTop = (elName: string) => {
        const el = document.getElementById(elName);
        if (el) {
            el.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        }
    };

    const scrollToBottom = (elName: string) => {
        const el = document.getElementById(elName);
        if (el) {
            el?.scrollTo({
                top: el.scrollHeight,
                behavior: 'smooth'
            });
        }
    };

    return (
        <>
            { serviceAvailable ? 
                <div style={{overflowX: 'hidden'}} className={`background ${alarmTriggered ? " blinkingTransitions " : " "}`}>
                    <TopPanel></TopPanel>
                    <TopPanelSpacer></TopPanelSpacer>
                    <IndicatorPanel></IndicatorPanel>
                    <ButtonWithDrawer flexDirection="column" buttonText="Alarm Control"><ArmButtonList alarmProfilesToDisplay={[0,1,3,15,2,7]}></ArmButtonList></ButtonWithDrawer>
                    <ButtonWithDrawer flexDirection="row" buttonText="Garage Door"><GarageDoorButton></GarageDoorButton></ButtonWithDrawer>
                    <ButtonWithDrawer flexDirection="column" justifyContent="flex-start" buttonText="Advanced">
                        <ButtonWithDrawer flexDirection="column" buttonText="Special Functions"><SpecialFunctions></SpecialFunctions></ButtonWithDrawer>
                        <ButtonWithDrawer flexDirection="column" justifyContent="flex-start" buttonText="Status" containsScrollable>
                            <div style={{display: "flex", gap: 10}}>
                                <Button onClick={(e) => {scrollToBottom("statusContainer")}} className="scrollToBottomBtn scroll-btn">Bottom</Button>
                                <Button onClick={(e) => {scrollToTop("statusContainer")}}  className="scrollToTopBtn scroll-btn">Top</Button>
                            </div>
                            <pre id="statusContainer" className="dimmable">{JSON.stringify(appState.status, null, 2)}</pre>
                        </ButtonWithDrawer>
                        <ButtonWithDrawer flexDirection="column" justifyContent="flex-start" buttonText="Past Events" containsScrollable>
                            <div style={{display: "flex", gap: 10}}>
                                <Button onClick={(e) => {scrollToBottom("eventsContainer")}} className="scrollToBottomBtn scroll-btn">Bottom</Button>
                                <Button onClick={(e) => {scrollToTop("eventsContainer")}}  className="scrollToTopBtn scroll-btn">Top</Button>
                            </div>
                            <pre id="eventsContainer" className="dimmable">{JSON.stringify(appState.pastEvents, null, 2)}</pre>
                        </ButtonWithDrawer>
                        <ButtonWithDrawer flexDirection="column" justifyContent="flex-start" buttonText="Profiles" containsScrollable>
                            <div style={{display: "flex", gap: 10}}>
                                <Button onClick={(e) => {scrollToBottom("profilesContainer")}} className="scrollToBottomBtn scroll-btn">Bottom</Button>
                                <Button onClick={(e) => {scrollToTop("profilesContainer")}}  className="scrollToTopBtn scroll-btn">Top</Button>
                            </div>
                            <pre id="profilesContainer" className="dimmable">{JSON.stringify(appState.alarmProfiles, null, 2)}</pre>
                        </ButtonWithDrawer>

                        <ButtonWithDrawer flexDirection="column" buttonText="Choose Alarm Profile"><ArmButtonList></ArmButtonList></ButtonWithDrawer>
                    </ButtonWithDrawer>
                </div> :
                <div>
                    <UnavailableOverlay>{appState.isError && !appState.isConnected ? unavailableContent : loadingContent}</UnavailableOverlay>
                </div>
            }
        </>
    );
};

export default AppView;