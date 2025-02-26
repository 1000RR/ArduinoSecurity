/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable no-unused-vars */
"use client";
import React from "react";
import styled, {css} from "styled-components";
import { emitGarageDoorToggleEvent } from "@src/WebSocketService";
import Button from "./Button";

const GarageDoorButton: React.FC<{
    className?: string
}> = ({ className }) => {
    const handler:React.MouseEventHandler<HTMLButtonElement> = function(event) {
        emitGarageDoorToggleEvent();
    };

    return (
    <>
        <Button className="dimmable garage_door_opener_button_color" onClick={(e)=>{e.currentTarget.blur(); handler(e);}}>
            <div>Activate Garage Door Opener</div>
        </Button>
    </>
    );
};

export default GarageDoorButton;