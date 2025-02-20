"use client";
import React from "react";
import styled, {css} from "styled-components";
import AlarmEnableButton from "@components/AlarmEnableButton"

export const PanelSizeStyle = css`
    width: 100%;
    min-width: 100%;
    height: 120px;

    @media only screen and (min-device-width: 320px) and (max-device-width: 430px) and (-webkit-device-pixel-ratio: 2), 
		only screen and (min-device-width: 375px) and (max-device-width: 812px) and (-webkit-device-pixel-ratio: 3) {
        height: 120px;
    }
`;

export const PanelLayoutStyle = css`
    display: flex;
    justify-content: center;
    align-items: start;
    justify-content: space-between;
    gap: 10px;
    flex-direction: column;
    padding: 10px 10px 10px 10px;
    border-radius: 5px;
    z-index: 10;
`;



const CompositeStyledPanel = styled.div`
    ${PanelSizeStyle}
    ${PanelLayoutStyle}
`;


const TopPanelSpacer: React.FC<{
    className?: string
}> = ({ className }) => {
    return (
        <CompositeStyledPanel className={className}></CompositeStyledPanel>
    );
};

export default TopPanelSpacer;