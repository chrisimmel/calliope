import React from "react";
import { createRoot } from "react-dom/client";
import ClioApp from "./ClioSwipeable";

const container = document.getElementById("root");
if (container) {
    const root = createRoot(container);
    container.classList.add("fullscreen");
    root.render(<ClioApp/>);
} else {
    console.error("The 'root' element wasn't found.");
}
