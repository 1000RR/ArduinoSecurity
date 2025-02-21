"use client";
import React from "react";
import Panel from "@components/Panel"
import { useSelector } from "react-redux";
import { AlarmProfile, AppStateSlice, StatusResponse } from "./AppStateSlice";
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
                name: (!alarmProfilesToDisplay.length ? `${index}: ` : ``) + alarmProfile.name,
                id: index,
                enabled: alarmArmed && selectedProfileNumber === index
            });
        }
    });

    const clickHandler:React.MouseEventHandler<HTMLButtonElement> = function(event) {
        const profileId =  Number.parseInt(event.currentTarget.id); //-1 is disable button manually added
        profileId === -1 ?  emitDisarmEvent() : emitArmAndChangeProfileEvent(profileId);
    };

    return (
        <Panel flexDirection="row" alignItems="center" gap={10} rowGap={30}>
            {generatedAlarmProfileList.map((alarmProfile: AlarmProfileDescriptor, index) => (
                <Button id={alarmProfile.id} key={index} onClick={clickHandler} className={(alarmProfile.enabled ? " alarm_button_enabled " : " alarm_button_disabled ") + " dimmable alarm_button"} >
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
 
 
