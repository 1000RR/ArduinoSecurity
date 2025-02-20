"use client";
import React from "react";
import styled, {css} from "styled-components";


export const PanelSizeStyle = css`
    width: 100%;
    height: content;
    min-height: 160px;
`;

export const PanelLayoutStyle = css`
    display: flex;
    justify-content: center;
    align-items: start;
    justify-content: space-evenly;
    gap: 20px;
    flex-direction: row;
    padding: 20px;
    flex-wrap: wrap;
`;

export const PanelBorderStyle = css`
    border-radius: 5px;
`;

const PanelColorStyle = css`
    background-color: rgba(60,60,60, .5);
`;


const CompositeStyledPanel = styled.div`
    ${PanelSizeStyle}
    ${PanelLayoutStyle}
    ${PanelColorStyle}
    ${PanelBorderStyle}
`;


const Panel: React.FC<{
    className?: string,
    children?: React.ReactNode
}> = ({ className, children }) => {
    
    return (
        <CompositeStyledPanel className={className}>
           {children}
        </CompositeStyledPanel>
    );
};

export default Panel;