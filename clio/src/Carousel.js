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

const Carousel = ({ children, onSelectItem, defaultIndex }) => {
    const boundDefaultIndex = Math.max(Math.min(defaultIndex, children.length), 0);
    const [activeIndex, setActiveIndex] = useState(boundDefaultIndex);

    const updateIndex = (newIndex) => {
        const childCount = React.Children.count(children);
        if (newIndex < 0) {
            newIndex = 0;
        } else if (newIndex >= childCount) {
            newIndex = childCount - 1;
        }

        if (newIndex != activeIndex) {
            setActiveIndex(newIndex);
            if (onSelectItem) {
                onSelectItem(newIndex);
            }
        }
    };

    const aheadOne = () => {
        updateIndex(activeIndex + 1);
    };
    const backOne = () => {
        updateIndex(activeIndex - 1);
    };
    const toStart = () => {
        updateIndex(0);
    };
    const toEnd = () => {
        updateIndex(React.Children.count(children));
    };

    const handlers = useSwipeable({
        onSwipedLeft: () => aheadOne(),
        onSwipedRight: () => backOne()
    });

    return (
        <div
            {...handlers}
            className="carousel">
            <div className="inner" style={{ transform: `translateX(-${activeIndex * 100}%)`}}>
                {React.Children.map(children, (child, index)=> {
                    return React.cloneElement(child, { width: "100%" });
                })}
            </div>
            <div className="nav">
                <button
                    onClick={() => {
                        toStart();
                    }}
                >
                    &lt;&lt;
                </button>
                <button
                    onClick={() => {
                        backOne();
                    }}
                >
                    &lt;
                </button>
                <button
                    onClick={() => {
                        aheadOne();
                    }}
                >
                    &gt;
                </button>
                <button
                    onClick={() => {
                        toEnd();
                    }}
                >
                    &gt;&gt;
                </button>
            </div>
        </div>
    );
};

export default Carousel;