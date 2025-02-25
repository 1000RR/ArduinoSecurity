/* eslint-disable @typescript-eslint/no-unused-expressions */
"use client";
import Image from "next/image";
import React from "react";
import { useSelector } from "react-redux";
import styled, {css} from "styled-components";
import { emitDisarmEvent, emitArmEvent } from "./WebSocketService";
import { AppStateSlice } from "./AppStateSlice";

const ButtonSizeStyle = css`
    width: 100%;
    height: 100px;
    font-size: 2em;

    @media only screen and (min-device-width: 320px) and (max-device-width: 430px) and (-webkit-device-pixel-ratio: 2), 
       only screen and (min-device-width: 375px) and (max-device-width: 812px) and (-webkit-device-pixel-ratio: 3)
    {
       width: calc(100vw - 20px);
       height: 100px;
       font-size: 1.5em;
    }
`;
const ButtonBorderStyle = css`
    border: 1px;
    border-style: solid;
    border-radius: 5px;
    border-color: darkgrey;
`;
const ButtonLayoutStyle = css`
    display: flex;
    justify-content: center;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-direction: row;
    padding: 10px;
`;

const ButtonTextStyle = css`
    font-family: "futura";
    font-size: 25px;
`;

const ButtonPressStyle = css`
    &.buttonEnabled {
        background-color: #00a0d0;
        &:focus {
            background-color: lightblue;
            border-color: white;
            color: white;
        }
        &:active {
            background-color: #0099ff;
            filter: saturate(1.2);
            color: white;
        }

        @media (prefers-color-scheme: dark) {
            filter: brightness(0.7);   
            color: white;
        }
    }

    &.buttonDisabled {
        background-color:  #d00000;
        &:focus {
            background-color: lightcoral;
            border-color: white;
        }
        &:active {
            background-color: #ff3300;
            filter: saturate(1.2);  
        }
        @media (prefers-color-scheme: dark) {
            filter: brightness(0.7);
            color: white;
        }
    }
`;

const CompositeStyledButton = styled.button`
    ${ButtonSizeStyle}
    ${ButtonBorderStyle}
    ${ButtonLayoutStyle}
    ${ButtonPressStyle}
    ${ButtonTextStyle}
`;

const AlarmEnableButton: React.FC<{
    className?: string,
    children?: React.ReactNode,
    onClick?: React.MouseEventHandler
}> = ({ className, children}) => {

    const imgSrcArmed = "/assets/attackdog.jpg";
    const imgSrcDisarmed = "/assets/dogue.jpg";

    const isArmed = useSelector(function (state: AppStateSlice) { 
        return state.appState.status?.armStatus === "ARMED"
    });

    const profileName = useSelector(function (state: AppStateSlice) { 
        return state.appState.status?.profile
    });

    const handler:React.MouseEventHandler<HTMLButtonElement> = function(event) {
        isArmed ? emitDisarmEvent() : emitArmEvent();
    };

    const buttonText = isArmed ? `ARMED : ${profileName.toUpperCase()}` : "DISARMED";
    const alarmTriggered = useSelector(function (state: AppStateSlice) { 
        return state.appState.status.alarmStatus === 'ALARM';
    });


    return (<div style={{ width: "100%", }}>
        <CompositeStyledButton className={`${className} ${isArmed ? 'buttonEnabled' : 'buttonDisabled'}`} onClick={handler}>
            <Image className={`fadeoutImageRound scale_mobile ${alarmTriggered ? 'invertTransitions' : ''}`} alt="" height="90" width="90" src={isArmed ? imgSrcArmed : imgSrcDisarmed}></Image><></>
                {buttonText}
                {children}
            
        </CompositeStyledButton>
        </div>
    );
};

export default AlarmEnableButton;