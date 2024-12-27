# Camera Plane Manager

A Blender addon for managing camera-aligned image planes with intuitive distance controls.

## Features

- Import images as planes that automatically align with cameras
- Automatic plane scaling based on camera FOV and distance
- Distance control through either:
  - Numeric input in the properties panel
  - Visual control using an empty object in the 3D viewport
- Support for camera shifts and proper perspective scaling
- Ability to add/remove visual distance controls at any time
- Maintains proper scaling when camera parameters change

## Installation

1. Download the latest release (`camera-plane-addon.py`)
2. Open Blender and go to Edit > Preferences
3. Click on the "Add-ons" section
4. Click "Install..." and select the downloaded file
5. Enable the addon by checking its checkbox
6. The addon requires "Import Images as Planes" to be enabled (will be automatically enabled)

## Usage

### Importing New Planes

1. Select a camera in your scene
2. In the Object Properties panel, find the "Camera Plane" section
3. Click "Import Camera Plane"
4. Select your image file(s)
5. Adjust the initial distance and scale settings
6. Choose whether to use an empty for distance control
7. Click "Import"

### Managing Existing Planes

For any camera-aligned plane:
1. Select the plane
2. In the Object Properties panel, find the "Camera Plane" section
3. Adjust the distance and scale values directly
4. Click "Add Empty Control" to add visual distance control
5. Click "Remove Empty Control" to remove visual control

### Using Empty Controls

When an empty control is active:
1. The empty appears at the camera's position
2. Move the empty freely in 3D space
3. The plane's distance updates based on the empty's position
4. The empty stays in place when the camera moves
5. Distance is calculated based on actual world-space distance

## Requirements

- Blender 4.0 or newer
- "Import Images as Planes" addon (automatically enabled)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Cristian Omar Jimenez

## Version

1.1.0
