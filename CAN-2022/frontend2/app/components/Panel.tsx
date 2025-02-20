"use client";
import React from "react";
import styled, {css} from "styled-components";

export type CSSAlignItems =
| 'flex-start'
| 'flex-end'
| 'center'
| 'baseline'
| 'stretch'
| 'start'
| 'end'
| 'self-start'
| 'self-end'
| 'normal'
| 'inherit'
| 'initial'
| 'unset';

export const PanelSizeStyle = css`
    width: 100%;
    height: content;
    min-height: 100px;
`;

export const PanelLayoutStyle = css`
    display: flex;
    justify-content: center;
    align-items: start;
    justify-content: space-evenly;
    gap: 10px;
    row-gap: 20px;
    flex-direction: row;
    padding: 20px 0px 20px 0px;
    flex-wrap: wrap;
    position: relative;
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
    children?: React.ReactNode,
    flexDirection?: 'row' | 'column',
    gap?: number,
    rowGap?: number,
    alignItems?: CSSAlignItems
}> = ({ className, children, flexDirection, gap, rowGap, alignItems }) => {
    
    return (
        <CompositeStyledPanel className={className} style={{flexDirection:flexDirection, gap:gap, rowGap: rowGap, alignItems: alignItems}}>
           {children}
        </CompositeStyledPanel>
    );
};

export default Panel;