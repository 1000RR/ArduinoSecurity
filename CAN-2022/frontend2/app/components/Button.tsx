

import React from "react";

const Button: React.FC<{
    className?: string,
    children?: React.ReactNode,
    buttonText?: string,
}> = ({ className, children, buttonText}) => {
    return (
        <button className={`base-button ${className}`}>
            <text>{buttonText}</text>
            {children}
        </button>
    );
};

export default Button;