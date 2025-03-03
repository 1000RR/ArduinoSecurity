

import React from "react";
import styled, {css} from "styled-components";

const ButtonSizeStyle = css`
    width: 100%;
    height: 65px;
    font-size: 1.7em;
    font-family: "futura";

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
    background-color:  #aaaaaa;
	color: #3c3c3c;
	border-color: #3c3c3c;
    transition-duration: .4s;
	
	&:focus {
		background-color: #bbbbbb;
		border-color: #3c3c3c;
		color: #3c3c3c;
	}

	&:active {
		background-color: #dddddd;
		border-color: #111111;
		color: #111111;
	}

	@media (prefers-color-scheme: dark) {
		background-color: #3c3c3c;
		color: #999999;
        border-color: #999999;

		&:focus {
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
`;


const Button: React.FC<{
    className?: string,
    children?: React.ReactNode,
    buttonText?: string,
    style?: React.CSSProperties,
    onClick?: React.MouseEventHandler<HTMLButtonElement>,
    id?: string
}> = ({ className, children, buttonText, style, onClick, id}) => {
    return (
        <CompositeStyledButton id={id} className={`${className} base-button`} style={style} onClick={(e)=>{e.currentTarget.blur(); onClick? onClick(e) : (()=>{})();}}>
            {buttonText}
            {children}
        </CompositeStyledButton>
    );
};

export default Button;