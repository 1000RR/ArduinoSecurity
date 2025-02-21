"use client";
import React from "react";
import styled, {css} from "styled-components";

export const SizePositionStyle = css`
	position: fixed;    
	height: 100%;
	min-height: 100%;
	width: 100%;
	min-width: 100%;
	z-index: 10;
`;

export const TextStyle = css`
	text-align: left;
	font-size: 40px;
	font-weight: normal;
	font-family: "futura";
	color: white;
	@media (prefers-color-scheme: dark) {
		color: #a5a5a5
	}
`;

const display = "flex";

export const BorderStyle = css`
	border: 1px;
	border-style: solid;
	border-radius: 5px;
	border-color: darkgrey;

	@media (prefers-color-scheme: dark) {
		border-color: #777777
	}
`;

export const LayoutStyle = css`
	display: ${display};
	justify-content: center;
	align-items: center;
	gap: 40px;
	flex-direction: column;
	padding: 10px;
`;

const Overlay = styled.div`
	${SizePositionStyle}
	${TextStyle}
	${LayoutStyle}
	${BorderStyle}
	background-color: rgba(55, 55, 55, .7);
`;

const UnavailableOverlay: React.FC<{children?: React.ReactNode}> = ({children}) => {
	return (
		<>
			<Overlay>{children}</Overlay>
		</>
	);
};

export default UnavailableOverlay;