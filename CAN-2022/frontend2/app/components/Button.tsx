

import React from "react";
import styled, {css} from "styled-components";

const ButtonSizeStyle = css`
    width: 100%;
    height: 80px;
    font-size: 2em;

    @media only screen and (min-device-width: 320px) and (max-device-width: 430px) and (-webkit-device-pixel-ratio: 2), 
       only screen and (min-device-width: 375px) and (max-device-width: 812px) and (-webkit-device-pixel-ratio: 3)
    {
       font-size: 1.5em;
    }
`;
const ButtonBorderStyle = css`
    border: 1px;
    border-style: solid;
    border-radius: 5px;
    border-color: darkgrey;
`;
const ButtonLayoutStyle = css`
    display: flex;
    justify-content: center;
    align-items: center;
    justify-content: space-around;
    gap: 10px;
    flex-direction: column;
`;
const ButtonPressStyle = css`
    
    &:active {
        background-color: #0F0F0F;
    }

    @media (prefers-color-scheme: dark) {   
        color: white;
    }
    

    
`;

const CompositeStyledButton = styled.button`
    ${ButtonSizeStyle}
    ${ButtonBorderStyle}
    ${ButtonLayoutStyle}
    ${ButtonPressStyle}
`;


const Button: React.FC<{
    className?: string,
    children?: React.ReactNode,
    buttonText?: string,
    style?: React.CSSProperties,
    onClick?: React.MouseEventHandler<HTMLButtonElement>,
    id?: number
}> = ({ className, children, buttonText, style, onClick, id}) => {
    return (
        <CompositeStyledButton id={id?.toString()} className={`base-button ${className}`} style={style} onClick={onClick}>
            {buttonText}
            {children}
        </CompositeStyledButton>
    );
};

export default Button;