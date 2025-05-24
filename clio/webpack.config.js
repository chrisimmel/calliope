const cuid2 = require("@paralleldrive/cuid2");
const path = require("path");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const fs = require('fs');
const webpack = require('webpack');

// Determine if we're building for mobile or web by checking for a special file
// that we'll create in the npm scripts
let isMobileBuild = false;
const mobileMarkerPath = path.join(__dirname, '.mobile-build');

// Determine environment (production vs development)
const isProduction = process.env.NODE_ENV === 'production';

try {
  if (process.env.MOBILE === '1' || fs.existsSync(mobileMarkerPath)) {
    isMobileBuild = true;
  }
} catch (e) {
  console.error('Error checking for mobile build:', e);
}

console.log(`Building for ${isMobileBuild ? 'MOBILE' : 'WEB'} in ${isProduction ? 'PRODUCTION' : 'DEVELOPMENT'} mode`);

module.exports = {
    entry: "./src/index.tsx",
    output: {
        filename: `main.js?${cuid2.createId()}`,
        path: path.resolve(__dirname, "build"),
        // Use root path for mobile builds, /clio/ for web builds
        publicPath: isMobileBuild ? "/" : "/clio/",
    },
    plugins: [
        new HtmlWebpackPlugin({
            template: path.join(__dirname, "public", "index.html"),
        }),
        // Define environment variables for client-side code
        new webpack.DefinePlugin({
            'process.env.NODE_ENV': JSON.stringify(isProduction ? 'production' : 'development'),
            'process.env.REACT_APP_ENV': JSON.stringify(isProduction ? 'production' : 'development'),
            'process.env.IS_MOBILE_BUILD': JSON.stringify(isMobileBuild)
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
