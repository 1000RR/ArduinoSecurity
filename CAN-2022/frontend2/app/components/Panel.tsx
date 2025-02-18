"use client";
import React from "react";
import styled, {css} from "styled-components";


export const PanelSizeStyle = css`
    width: 100%;
    height: 165px;
`;

export const PanelLayoutStyle = css`
    display: flex;
    justify-content: center;
    align-items: start;
    justify-content: space-between;
    gap: 10px;
    flex-direction: row;
    padding: 20px;
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