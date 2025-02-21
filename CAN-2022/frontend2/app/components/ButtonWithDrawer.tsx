/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable no-unused-vars */
"use client";
import React, {useState} from "react";
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
    font-size: 23px;
    font-weight: normal;
    font-family: "futura";
`;

export const ButtonBorderStyle = css`
    border: 1px;
    border-style: solid;
    border-radius: 5px;
    border-color: darkgrey;
    margin: 10px 10px 0px 10px;
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
        color: #999999;

        &:hover {
            color: #c5c5c5;
            background-color: #454545;
            border-color: #aaaaaa;
        }

        &:active {
            color: #d5c5c5;
            background-color: #6f6f6f;
            border-color: black;
        }

        .button-enabled {
            color: white !important;
            background-color: red !important;
            border-color: white !important; 
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
    const handler:React.MouseEventHandler<HTMLButtonElement> = function(event) {
        setIsCollapsed(!isCollapsed);
        event.currentTarget.blur();
    };

    return (
    <>
        <CompositeStyledButton className={`${className} ${isCollapsed ? '' : 'button-enabled'}`} onClick={handler}>
            {buttonText}
        </CompositeStyledButton>
        <Drawer style={{flexDirection: flexDirection, display: isCollapsed ? 'none' : 'flex', justifyContent: justifyContent}} className={isCollapsed ? 'collapsed' : ''}>
            {!isCollapsed && children}
        </Drawer>
    </>
    );
};

export default ButtonWithDrawer;