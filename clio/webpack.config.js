const cuid2 = require("@paralleldrive/cuid2");
const path = require("path");
const HtmlWebpackPlugin = require("html-webpack-plugin");

module.exports = {
    entry: "./src/index.tsx",
    output: {
        filename: `main.js?${cuid2.createId()}`,
        path: path.resolve(__dirname, "build"),
    },
    plugins: [
        new HtmlWebpackPlugin({
            template: path.join(__dirname, "public", "index.html"),
        }),
    ],
    devServer: {
        static: {
            directory: path.join(__dirname, "build"),
        },
        port: 3000,
    },
    module: {
        // exclude node_modules
        rules: [
            {
                test: /\.tsx?$/,
                use: 'ts-loader',
                exclude: /node_modules/,
                //test: /\.(js|jsx)$/,
                //exclude: /node_modules/,
                //use: ["babel-loader"],
            },
            {
                test: /\.css$/i,
                use: ["style-loader", "css-loader"],
            },
        ],
    },
    // pass all js files through Babel
    resolve: {
        //extensions: ["*", ".js", ".jsx"],
        extensions: ['.tsx', '.ts', '.js'],
    },
};
