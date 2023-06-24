import React from "react";
import { createRoot } from "react-dom/client";
import ClioApp from "./ClioSwipeable";

const container = document.getElementById("root");
const root = createRoot(container);
root.render(<ClioApp />);
