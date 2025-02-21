/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable no-unused-vars */
"use client";
import React from "react";
import styled, {css} from "styled-components";
import { emitGarageDoorToggleEvent } from "@components/WebSocketService";

export const ButtonSizeStyle = css`
    width: calc(100% - 10px);
    height: 85px;

    @media only screen and (min-device-width: 320px) and (max-device-width: 430px) and (-webkit-device-pixel-ratio: 2), 
       only screen and (min-device-width: 375px) and (max-device-width: 812px) and (-webkit-device-pixel-ratio: 3)
    {
       width: calc(100vw - 20px);
    }
`;

export const ButtonTextStyle = css`
    text-align: left;
    font-weight: bold;
    font-size: 1.25em;
    font-family: "futura";
`;

export const ButtonBorderStyle = css`
    border: 1px;
    border-style: solid;
    border-radius: 5px;
`;

export const ButtonLayoutStyle = css`
    display: flex;
    justify-content: center;
    align-items: center;
    justify-content: space-around;
    flex-direction: row;
`;

export const ButtonPressStyle = css`
    background-color: #39644E;
    border-color: #bbbbbb;
    color: #bbbbbb;
    
    &:hover {
        background-color: #4d8a6a;
        border-color: #dddddd;
        color: #dddddd;
    }

    &:active {
        background-color: #71bb95;
        border-color: #ffffff;
        color: #ffffff;
    }
    
    @media (prefers-color-scheme: dark) {
        
    }
`;

const CompositeStyledButton = styled.button`
    ${ButtonTextStyle}    
    ${ButtonSizeStyle}
    ${ButtonBorderStyle}
    ${ButtonLayoutStyle}
    ${ButtonPressStyle}
`;

const GarageDoorButton: React.FC<{
    className?: string
}> = ({ className }) => {
    const handler:React.MouseEventHandler<HTMLButtonElement> = function(event) {
        event.currentTarget.blur();
        emitGarageDoorToggleEvent();
    };

    return (
    <>
        <CompositeStyledButton className="dimmable" onClick={handler}>
            <div>Activate Garage Door Opener</div>
        </CompositeStyledButton>
    </>
    );
};

export default GarageDoorButton;