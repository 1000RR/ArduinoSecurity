/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable no-unused-vars */
"use client";
import React from "react";
import styled, {css} from "styled-components";
import { emitGarageDoorToggleEvent } from "@src/WebSocketService";
import Button from "./Button";

const GarageDoorButton: React.FC<{
    className?: string,
    margin?: string
}> = ({ className, margin }) => {
    const handler:React.MouseEventHandler<HTMLButtonElement> = function(event) {
        emitGarageDoorToggleEvent();
    };

    return (
    <>
        <Button className="dimmable garage_door_opener_button_color" style={{margin: margin}} onClick={(e)=>{e.currentTarget.blur(); handler(e);}}>
            <div>Activate Garage Door Opener</div>
        </Button>
    </>
    );
};

export default GarageDoorButton;