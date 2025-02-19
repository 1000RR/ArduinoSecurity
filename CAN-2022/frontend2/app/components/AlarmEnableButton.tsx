"use client";
import Image from "next/image";
import React, {useState} from "react";
import styled, {css} from "styled-components";

export const ButtonSizeStyle = css`
    width: 100%;
    height: 145px;

    @media only screen and (min-device-width: 320px) and (max-device-width: 430px) and (-webkit-device-pixel-ratio: 2), 
       only screen and (min-device-width: 375px) and (max-device-width: 812px) and (-webkit-device-pixel-ratio: 3)
    {
       width: calc(100vw - 20px);
       font-size: 1.5em;
    }
`;
export const ButtonBorderStyle = css`
    border: 1px;
    border-style: solid;
    border-radius: 5px;
    border-color: darkgrey;
`;
export const ButtonLayoutStyle = css`
    display: flex;
    justify-content: center;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-direction: row;
    padding: 10px;
`;
export const ButtonPressStyle = css`
    &.buttonEnabled {
        background-color: #00a0d0;
        &:hover {
            background-color: lightblue;
            border-color: white;
        }
        &:active {
            background-color: #0099ff;
            filter: saturate(1.2);  
        }

        @media (prefers-color-scheme: dark) {
            filter: brightness(0.7);       
        }
    }

    &.buttonDisabled {
        background-color:  #d00000;
        &:hover {
            background-color: lightcoral;
            border-color: white;
        }
        &:active {
            background-color: #ff3300;
            filter: saturate(1.2);  
        }
        @media (prefers-color-scheme: dark) {
            filter: brightness(0.7);
            color: lightgray;
        }
    }
`;

const CompositeStyledButton = styled.button`
    ${ButtonSizeStyle}
    ${ButtonBorderStyle}
    ${ButtonLayoutStyle}
    ${ButtonPressStyle}
`;

const AlarmEnableButton: React.FC<{
    className?: string,
    children?: React.ReactNode,
    imgSrc?: string,
    onClick?: React.MouseEventHandler
}> = ({ className, children, imgSrc}) => {
    
    const [isEnabled, setIsEnabled] = useState(false);

    const handler:React.MouseEventHandler = function() {
        setIsEnabled(!isEnabled);
    };

    const buttonText = "TEMP TEXT";

    return (<div style={{ width: "100%", }}>
        <CompositeStyledButton className={`${className} ${isEnabled ? 'buttonEnabled' : 'buttonDisabled'}`} onClick={handler}>
            {imgSrc? <Image alt="" width="100" height="75" src={imgSrc}></Image> : <></>}
                {buttonText}
                {children}
            
        </CompositeStyledButton>
        </div>
    );
};

export default AlarmEnableButton;