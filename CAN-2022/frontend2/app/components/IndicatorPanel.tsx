"use client";
import React from "react";
import styled, {css} from "styled-components";
import Panel from "@components/Panel"

export const PanelSizeStyle = css`
    width: 100%;
    height: 330px;
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
    background-color: rgba(60,60,60, .3);
`;


const CompositePanelStyle = styled.div`
    ${PanelSizeStyle}
    ${PanelLayoutStyle}
    ${PanelColorStyle}
`;


const IndicatorPanel: React.FC<{
    className?: string
}> = ({ className}) => {
    
    return (
        <CompositePanelStyle className={className}>
             <Panel></Panel>
             <Panel></Panel>
        </CompositePanelStyle>
    );
};

export default IndicatorPanel;
 
 
