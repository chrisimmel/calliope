// Ambient module declarations for non-code imports so `ts-loader` resolves
// stylesheet side-effect imports (app CSS + self-hosted @fontsource faces).
declare module '*.css';
