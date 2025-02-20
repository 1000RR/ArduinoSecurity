/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable no-unused-vars */
"use client";
import React, {useRef, useState} from "react";
import styled, {css} from "styled-components";

const drawerDisplay = 'flex';

export const ButtonSizeStyle = css`
    width: calc(100% - 20px);
    height: 75px;

    @media only screen and (min-device-width: 320px) and (max-device-width: 430px) and (-webkit-device-pixel-ratio: 2), 
       only screen and (min-device-width: 375px) and (max-device-width: 812px) and (-webkit-device-pixel-ratio: 3)
    {
       width: calc(100vw - 20px);
       font-size: 1.5em;
    }
`;

export const ButtonTextStyle = css`
    text-align: left;
    font-size: 20px;
    font-weight: bold;
`;

export const ButtonBorderStyle = css`
    border: 1px;
    border-style: solid;
    border-radius: 5px;
    border-color: darkgrey;
    margin: 10px 10px 0px 10px;

    @media (prefers-color-scheme: dark) {
        border-color: #777777
    }
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
    background-color:  #c5c5c5;
    color: #3c3c3c;
    &:hover {
        background-color: #3c3c3c;
        border-color: white;
        color: #c5c5c5;
    }
    
    @media (prefers-color-scheme: dark) {
        background-color: #3c3c3c;
        color: #c5c5c5;

        &:hover {
            color: #3c3c3c;
            background-color: #c5c5c5;
            border-color: black;
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

const Drawer = styled.div`
    width: calc(100% - 20px);
    min-height: 100px;
    background-color: rgba(55, 55, 55, .4);
    margin: 0px 10px 5px 10px;
    border-radius: 5px;
    display: ${drawerDisplay};
    gap: 10px;
    padding: 10px;
    justify-content: space-around; 
    align-items: center;
    overflow: auto;
`;

const ButtonWithDrawer: React.FC<{
    flexDirection: ('row' | 'column'),
    className?: string,
    children?: React.ReactNode,
    buttonText?: string,
    justifyContent? : ('space-around' | 'space-between' | 'center' | 'flex-start' | 'flex-end'),
    onClick?: React.MouseEventHandler,
}> = ({ flexDirection, className, children, buttonText, justifyContent}) => {
    
    const [isCollapsed, setIsCollapsed] = useState(true);
    const inputRef = useRef(null);
    const handler:React.MouseEventHandler<HTMLButtonElement> = function(event) {
        event.currentTarget.blur();
        setIsCollapsed(!isCollapsed);
    };

    return (
    <>
        <CompositeStyledButton ref={inputRef} className={`${className} ${isCollapsed ? 'buttonEnabled' : 'buttonDisabled'}`} onClick={handler}>
            {buttonText}
        </CompositeStyledButton>
        <Drawer style={{flexDirection: flexDirection, display: isCollapsed ? 'none' : 'flex', justifyContent: justifyContent}} className={isCollapsed ? 'collapsed' : ''}>
            {!isCollapsed && children}
        </Drawer>
    </>
    );
};

export default ButtonWithDrawer;