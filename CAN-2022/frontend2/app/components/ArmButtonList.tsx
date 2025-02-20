"use client";
import React, { useRef } from "react";
import Panel from "@components/Panel"
import { useSelector } from "react-redux";
import { AlarmProfile, AlarmProfilesResponse, AppState, AppStateSlice, StatusResponse } from "./AppStateSlice";
import Button from "./Button";
import { emitDisarmEvent, emitArmAndChangeProfileEvent } from "./WebSocketService";

type AlarmProfileDescriptor = {
    id: number,
    name: string,
    enabled: boolean
};

const ArmButtonContainer: React.FC<{
    className?: string,
    alarmProfilesToDisplay?: Array<number>
}> = ({ className, alarmProfilesToDisplay = []}) => {

    const alarmProfiles = useSelector(function (state: AppStateSlice) { 
        return state.appState.alarmProfiles.profiles;
    });
    const selectedProfileNumber = useSelector(function (state: AppStateSlice) { 
        return Number((state.appState.status as StatusResponse).profileNumber);
    });
    const alarmArmed = useSelector(function (state: AppStateSlice) { 
        return state.appState.status.armStatus === 'ARMED';
    });
    const generatedAlarmProfileList:Array<AlarmProfileDescriptor> = [{
        name: "Disarm",
        id: -1,
        enabled: !alarmArmed
    }];

    alarmProfiles?.forEach((alarmProfile: AlarmProfile, index: number) => {
        if (alarmProfilesToDisplay.length && alarmProfilesToDisplay.includes(index) || !alarmProfilesToDisplay.length) {
            generatedAlarmProfileList.push({
                name: alarmProfile.name,
                id: index,
                enabled: alarmArmed && selectedProfileNumber === index
            });
        }
    });

    const clickHandler:React.MouseEventHandler<HTMLButtonElement> = function(event) {
        let profileId =  Number.parseInt(event.currentTarget.id); //-1 is disable button manually added
        profileId === -1 ?  emitDisarmEvent() : emitArmAndChangeProfileEvent(profileId);
    };

    return (
        <Panel flexDirection="column" alignItems="center" gap={20}>
            {generatedAlarmProfileList.map((alarmProfile: AlarmProfileDescriptor, index) => (
                <Button id={alarmProfile.id} key={index} onClick={clickHandler} className={(alarmProfile.enabled ? " highlight_button_active " : " highlight_button_inactive ") + " thin_round_border dimmable alarm_button_margin"} >
                    {alarmProfile.name}
                </Button>
            ))}
        </Panel>
    );
};


const ArmButtonList: React.FC<{
    className?: string,
    alarmProfilesToDisplay?: Array<number>
}> = ({ className, alarmProfilesToDisplay }) => {
    return (
       <ArmButtonContainer alarmProfilesToDisplay={alarmProfilesToDisplay}></ArmButtonContainer>
    );
};

export default ArmButtonList;
 
 
