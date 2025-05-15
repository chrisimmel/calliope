import React from "react";
import { useSwipeable } from "react-swipeable";

import "./Carousel.css";

type CarouselItemProps = {
    children?: React.ReactNode
    width?: number,
    key?: string | number,
}

export const CarouselItem = ({ children, width }: CarouselItemProps) => {
    return (
        <div className="carousel-item" style={{ width: width || '100%' }}>
            {children}
        </div>
    );
};


type CarouselProps = {
    children?: React.ReactNode
    selectedIndex: number,
    incrementSelectedIndex: () => void,
    decrementSelectedIndex: () => void,
    skipAnimation?: boolean,
}

const Carousel = ({ children, selectedIndex, incrementSelectedIndex, decrementSelectedIndex, skipAnimation = false }: CarouselProps) => {
    const handlers = useSwipeable({
        onSwipedLeft: () => incrementSelectedIndex(),
        onSwipedRight: () => decrementSelectedIndex(),
        onSwipedUp: () => {},
        onSwipedDown: () => {},
        //preventScrollOnSwipe: true,
        touchEventOptions: { passive: false },
    });

    // Add a style with or without transition based on skipAnimation
    const innerStyle = {
        transform: `translateX(-${selectedIndex * 100}%)`,
        transition: skipAnimation ? 'none' : 'transform 0.3s'
    };

    return (
        <div
            {...handlers}
            className="carousel">
            <div className="inner" style={innerStyle}>
                {children}
            </div>
        </div>
    );
};

export default Carousel;
