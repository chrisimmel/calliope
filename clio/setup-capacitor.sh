
#!/bin/bash
set -e

echo "=== Setting up Capacitor for Clio (Fresh Install) ==="
cd /Users/chrisimmel/exp/calliope/clio

# Cleanup previous Capacitor installation
echo "Cleaning up previous Capacitor installation..."

# Remove iOS and Android directories if they exist
if [ -d "ios" ]; then
echo "Removing iOS directory..."
rm -rf ios
fi

if [ -d "android" ]; then
echo "Removing Android directory..."
rm -rf android
fi

# Remove Capacitor configuration
if [ -f "capacitor.config.ts" ] || [ -f "capacitor.config.js" ] || [ -f "capacitor.config.json" ]; then
echo "Removing Capacitor configuration files..."
rm -f capacitor.config.*
fi

# Save original package.json
echo "Backing up package.json..."
cp package.json package.json.original

# Remove Capacitor dependencies from package.json
echo "Removing Capacitor dependencies from package.json..."
node -e '
const fs = require("fs");
const packageJson = JSON.parse(fs.readFileSync("package.json", "utf8"));

// Remove all @capacitor/* dependencies
Object.keys(packageJson.dependencies || {}).forEach(dep => {
if (dep.startsWith("@capacitor/")) {
    delete packageJson.dependencies[dep];
}
});

Object.keys(packageJson.devDependencies || {}).forEach(dep => {
if (dep.startsWith("@capacitor/")) {
    delete packageJson.devDependencies[dep];
}
});

// Remove capacitor-related scripts
const scriptsToRemove = ["ios", "android", "build-mobile", "cap"];
scriptsToRemove.forEach(script => {
if (packageJson.scripts && packageJson.scripts[script]) {
    delete packageJson.scripts[script];
}
});

fs.writeFileSync("package.json", JSON.stringify(packageJson, null, 2));
'

# Clean npm cache to ensure fresh install
echo "Cleaning npm cache..."
npm cache clean --force

# Install Capacitor from scratch
echo "Installing Capacitor core packages..."
npm install @capacitor/core @capacitor/cli --save-exact

# Initialize Capacitor
echo "Initializing Capacitor..."
npx cap init Calliope com.chrisimmel.calliope.app --web-dir build

# Install plugins one by one
echo "Installing Capacitor plugins..."
npm install @capacitor/camera --save-exact
npm install @capacitor/device --save-exact
npm install @capacitor/filesystem --save-exact
npm install @capacitor/geolocation --save-exact
npm install @capacitor/status-bar --save-exact
npm install @capacitor/splash-screen --save-exact
npm install @capacitor/storage --save-exact
npm install @capacitor-community/voice-recorder --save-exact

# Update scripts in package.json
echo "Adding mobile scripts to package.json..."
node -e '
const fs = require("fs");
const packageJson = JSON.parse(fs.readFileSync("package.json", "utf8"));

packageJson.scripts = {
...packageJson.scripts,
"build-mobile": "webpack --mode production && npx cap sync",
"ios": "npm run build-mobile && npx cap open ios",
"android": "npm run build-mobile && npx cap open android"
};

fs.writeFileSync("package.json", JSON.stringify(packageJson, null, 2));
'

# Build the web app
echo "Building the web app..."
npm run build

# Add native platforms
echo "Adding iOS platform..."
npx cap add ios

echo "Adding Android platform..."
npx cap add android

# Configure iOS permissions
echo "Configuring iOS permissions..."
if [ -d "ios/App/App" ]; then
# Use PlistBuddy to add permissions if available
if [ -x "$(command -v /usr/libexec/PlistBuddy)" ]; then
    echo "Adding iOS permissions with PlistBuddy..."

    # Add each permission
    permissions=(
    "NSCameraUsageDescription:We need camera access to take pictures for story creation"
    "NSMicrophoneUsageDescription:We need microphone access to record audio for story creation"
    "NSPhotoLibraryAddUsageDescription:We need photo library access to save your stories"
    "NSPhotoLibraryUsageDescription:We need photo library access to select images for your stories"
    "NSLocationWhenInUseUsageDescription:Your location is used to provide location-aware story experiences"
    "NSLocationAlwaysAndWhenInUseUsageDescription:Your location is used to provide location-aware story experiences"
    )

    for permission in "${permissions[@]}"; do
    key="${permission%%:*}"
    value="${permission#*:}"

    if ! /usr/libexec/PlistBuddy -c "Print :$key" ios/App/App/Info.plist > /dev/null 2>&1; then
        /usr/libexec/PlistBuddy -c "Add :$key string '$value'" ios/App/App/Info.plist
    fi
    done
else
    echo "PlistBuddy not found. Please manually add permissions to ios/App/App/Info.plist"
    echo "Required permissions: Camera, Microphone, Photo Library, Location"
fi
else
echo "iOS app folder not found. There might be an issue with the iOS platform addition."
fi

# Configure Android permissions
echo "Configuring Android permissions..."
if [ -d "android/app/src/main" ]; then
# Check if permissions are already added
if ! grep -q "android.permission.CAMERA" android/app/src/main/AndroidManifest.xml; then
    # Create a temporary file with permissions
    permissions=(
    '<uses-permission android:name="android.permission.INTERNET" />'
    '<uses-permission android:name="android.permission.CAMERA" />'
    '<uses-permission android:name="android.permission.RECORD_AUDIO" />'
    '<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />'
    '<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />'
    '<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />'
    '<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />'
    )

    # Add permissions to AndroidManifest.xml before the application tag
    manifestFile="android/app/src/main/AndroidManifest.xml"
    tempFile="android_manifest.tmp"

    # Check if the file exists
    if [ -f "$manifestFile" ]; then
    # Create temp file
    cp "$manifestFile" "$tempFile"

    # Process the file line by line
    while IFS= read -r line; do
        echo "$line" >> new_manifest.xml
        # If we find the manifest tag, add all permissions after it
        if [[ $line == *"<manifest"*">"* ]]; then
        for permission in "${permissions[@]}"; do
            echo "    $permission" >> new_manifest.xml
        done
        fi
    done < "$tempFile"

    # Replace the original file
    mv new_manifest.xml "$manifestFile"

    # Clean up
    rm "$tempFile"
    else
    echo "AndroidManifest.xml not found at $manifestFile"
    fi
else
    echo "Android permissions already added to AndroidManifest.xml"
fi
else
echo "Android app folder not found. There might be an issue with the Android platform addition."
fi

# Final sync to ensure all configurations are applied
echo "Final sync with Capacitor..."
npx cap sync

echo "=== Fresh Capacitor setup complete! ==="
echo "To open in Xcode: npm run ios"
echo "To open in Android Studio: npm run android"
echo "Make sure you have Xcode or Android Studio installed and configured."
