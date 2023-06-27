import React, { useState } from "react";
import { useSwipeable } from "react-swipeable";

import "./Carousel.css";

export const CarouselItem = ({ children, width }) => {
    return (
        <div className="carousel-item" style={{ width: width }}>
            {children}
        </div>
    );
};

const Carousel = ({ children, selectedIndex, incrementSelectedIndex, decrementSelectedIndex }) => {
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
