"use client";
import React, { useRef } from "react";
import styled, {css} from "styled-components";
import Panel from "@components/Panel"
import { useSelector } from "react-redux";
import { AlarmProfilesResponse, AppState, AppStateSlice, StatusResponse } from "./AppStateSlice";

type DeviceDescriptor = {
    id: string,
    name: string,
    enabled: boolean,
    missing: boolean,
    triggered: boolean
};

export const PanelSizeStyle = css`
    width: 100%;
    height: content;
`;

export const PanelLayoutStyle = css`
    display: flex;
    justify-content: center;
    align-items: start;
    justify-content: space-between;
    gap: 10px;
    flex-direction: row;
    flex-wrap: wrap;
    padding: 10px 10px 10px 10px;
    border-radius: 5px;
`;

const PanelColorStyle = css`
    background-color: rgba(60,60,60, .3);
`;


const CompositePanelStyle = styled.div`
    ${PanelSizeStyle}
    ${PanelLayoutStyle}
    ${PanelColorStyle}
`;

const SensorsPanel: React.FC<{
    className?: string
}> = ({ className }) => {

    const deviceList:Array<DeviceDescriptor> = [];

    const stateDeviceList = useSelector(function (state: AppStateSlice) { 
        return state.appState.status.memberDevicesReadable.slice(0).sort((a: string, b:string) => a.localeCompare(b));
    });
    const garageOpen = useSelector(function (state: AppStateSlice) { 
        return (state.appState.status as StatusResponse).garageOpen;
    });
    const profileNumber = useSelector(function (state: AppStateSlice) { 
        return Number((state.appState.status as StatusResponse).profileNumber);
    });
    const myAlarmProfile = useSelector(function (state: AppStateSlice) { 
        return (state.appState.alarmProfiles as AlarmProfilesResponse).profiles[profileNumber];
    });
    const sensorsThatTriggerAlarm = myAlarmProfile?.sensorsThatTriggerAlarm;
    const missingDevices = useSelector(function (state: AppStateSlice) { 
        return state.appState.status.currentMissingDevices;
    });
    const triggeredDevices = useSelector(function (state: AppStateSlice) { 
        return state.appState.status.currentTriggeredDevices;
    });
    const alarmArmed = useSelector(function (state: AppStateSlice) { 
        return state.appState.status.armStatus === 'ARMED';
    });

    stateDeviceList?.forEach((device: string) => {
        if (device.indexOf('SENSOR |') == 0) {
            let name = device.substring(9, device.indexOf('| 0x')-1);
            let id = device.substring(device.indexOf('| 0x')+2);

            deviceList.push({
                name: name,
                id: id,
                enabled: alarmArmed && (!sensorsThatTriggerAlarm || sensorsThatTriggerAlarm.includes(id)),
                missing: missingDevices && missingDevices.includes(id),
                triggered: triggeredDevices && triggeredDevices.includes(id),
            });
        }
    });


    return (
        <Panel>
            <div style={{zIndex: -1, position: "absolute", top: 0, left: 5}}>{deviceList.length}</div>
            {deviceList.map((sensorElement, index) => (
                <div key={index} id={sensorElement.id} className={(sensorElement.triggered ? " invertTransitions " : "") + " thin_round_border status_icon_container_layout lower_opacity icon lowlight_gray" + (sensorElement.enabled && !sensorElement.missing ? " highlight_green " : "") + (sensorElement.missing ? " highlight_red " : "") + " dimmable"} >
                    {sensorElement.name.toLowerCase().indexOf("garage car door") > -1 
                        ? <img  src={garageOpen ? "/assets/garage_open.png" : "/assets/garage_closed.png"}></img> 
                        : sensorElement.name}
                </div>
            ))}
        </Panel>
    );
};

const AlarmsPanel: React.FC<{
    className?: string
}> = ({ className}) => {

    const deviceList:Array<DeviceDescriptor> = [];

    const stateDeviceList = useSelector(function (state: AppStateSlice) { 
        return state.appState.status.memberDevicesReadable.slice(0).sort((a: string, b:string) => a.localeCompare(b));
    });

    const profileNumber = useSelector(function (state: AppStateSlice) { 
        return Number((state.appState.status as StatusResponse).profileNumber);
    });
    const myAlarmProfile = useSelector(function (state: AppStateSlice) { 
        return (state.appState.alarmProfiles as AlarmProfilesResponse).profiles[profileNumber];
    });
    const enabledAlarmDevices = myAlarmProfile?.alarmOutputDevices;
    const missingDevices = useSelector(function (state: AppStateSlice) { 
        return state.appState.status.currentMissingDevices;
    });
    const triggeredDevices = useSelector(function (state: AppStateSlice) { 
        return state.appState.status.currentTriggeredDevices;
    });
    const alarmArmed = useSelector(function (state: AppStateSlice) { 
        return state.appState.status.armStatus === 'ARMED';
    });

    stateDeviceList?.forEach((device: string) => {
        if (device.indexOf('ALARM |') == 0) {
            let name = device.substring(8, device.indexOf('| 0x')-1);
            let id = device.substring(device.indexOf('| 0x')+2);

            deviceList.push({
                name: name,
                id: id,
                enabled: alarmArmed && (!enabledAlarmDevices || enabledAlarmDevices.includes(id)),
                missing: missingDevices && missingDevices.includes(id),
                triggered: triggeredDevices && triggeredDevices.includes(id),
            });
        }
    });
    
    return (<Panel>
        <div style={{zIndex: -1, position: "absolute", top: 0, left: 5}}>{deviceList.length}</div>
        {deviceList.map((alarmElement, index) => (
            <div key={index} id={alarmElement.id} className={(alarmElement.triggered ? " invertTransitions " : "") + " thin_round_border status_icon_container_layout lower_opacity icon lowlight_gray" + (alarmElement.enabled ? " highlight_green " : "") + (alarmElement.missing ? " highlight_red " : "") + " dimmable"} >
                 {alarmElement.name}
             </div>
        ))}
    </Panel>);
};

const IndicatorPanel: React.FC<{
    className?: string
}> = ({ className}) => {
    return (
        <CompositePanelStyle className={className}>
             <SensorsPanel></SensorsPanel>
             <AlarmsPanel ></AlarmsPanel>
        </CompositePanelStyle>
    );
};

export default IndicatorPanel;
 
 
