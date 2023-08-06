import React, { useState } from "react";
import { useSwipeable } from "react-swipeable";

import "./Carousel.css";

type CarouselItemProps = {
    children?: React.ReactNode
    width?: number,
    key?: string | number,
}

export const CarouselItem = ({ children, width }: CarouselItemProps) => {
    return (
        <div className="carousel-item" style={{ width: width }}>
            {children}
        </div>
    );
};


type CarouselProps = {
    children?: React.ReactNode
    selectedIndex: number,
    incrementSelectedIndex: () => void,
    decrementSelectedIndex: () => void,
}

const Carousel = ({ children, selectedIndex, incrementSelectedIndex, decrementSelectedIndex }: CarouselProps) => {
    const handlers = useSwipeable({
        onSwipedLeft: () => incrementSelectedIndex(),
        onSwipedRight: () => decrementSelectedIndex()
    });

    return (
        <div
            {...handlers}
            className="carousel">
            <div className="inner" style={{ transform: `translateX(-${selectedIndex * 100}%)`}}>
                {children}
            </div>
        </div>
    );
};

export default Carousel;
