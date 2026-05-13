import React from "react";
import { createRoot } from "react-dom/client";

import AppRoutes from "./routes/AppRoutes";

const container = document.getElementById("root");
if (container) {
    const root = createRoot(container);
    container.classList.add("fullscreen");
    root.render(<AppRoutes />);
} else {
    console.error("The 'root' element wasn't found.");
}
