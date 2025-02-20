/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable no-unused-vars */
"use client";
import React, {useRef} from "react";
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
    font-size: 1.5em;
`;

export const ButtonBorderStyle = css`
    border: 1px;
    border-style: solid;
    border-radius: 5px;
    border-color: darkgrey;

    @media (prefers-color-scheme: dark) {
        border-color: #777777
    }
`;

export const ButtonLayoutStyle = css`
    display: flex;
    justify-content: center;
    align-items: center;
    justify-content: space-around;
    flex-direction: row;
`;

export const ButtonPressStyle = css`
    background-color: rgba(85,150,118,1);
    color: #3c3c3c;
    &:active {
        background-color: rgba(57,100,78,1);
        border-color: white;
        color: #c5c5c5;
    }
    
    @media (prefers-color-scheme: dark) {
        background-color: rgba(57,100,78,1);
        color: #c5c5c5;

        &:active {
            color: #3c3c3c;
            background-color: rgba(85,150,118,1);
            border-color: black;
        }
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
    
    const inputRef = useRef(null);
    const handler:React.MouseEventHandler = function() {
        if (inputRef !== null && inputRef.current) { inputRef.current.blur() }
        emitGarageDoorToggleEvent();
    };

    return (
    <>
        <CompositeStyledButton ref={inputRef} onClick={handler}>
            <div>Garage Door</div>
        </CompositeStyledButton>
        
    </>
    );
};

export default GarageDoorButton;