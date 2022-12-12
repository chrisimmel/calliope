import React from "react";
import { createRoot } from "react-dom/client";
import ClioApp from "./ClioApp";

const container = document.getElementById("root");
const root = createRoot(container);
root.render(<ClioApp />);
