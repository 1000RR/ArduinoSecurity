"use client";
import React from "react";
import styled, {css} from "styled-components";
import AlarmEnableButton from "@components/AlarmEnableButton"

export const PanelSizeStyle = css`
    width: 100%;
    min-width: 100%;
    height: 165px;
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
`;

const PanelColorStyle = css`
    background-color: rgba(60,60,60, 1);
`;


const CompositeStyledPanel = styled.div`
    ${PanelSizeStyle}
    ${PanelLayoutStyle}
    ${PanelColorStyle}
`;


const TopPanel: React.FC<{
    className?: string
}> = ({ className }) => {
    return (
        <CompositeStyledPanel className={className}>
            <AlarmEnableButton className="button"></AlarmEnableButton>
        </CompositeStyledPanel>
    );
};

export default TopPanel;