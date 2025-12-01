# Scandroid Bridge Setup

This repository acts as a bridge between your device's filesystem and GitHub.

## Current Status
- **Snapshot**: `groot.html` contains a snapshot of the device's root directory.

## How to Update the Bridge
To update the snapshot from your device:

1.  **Generate Listing**: Open your browser on the device and navigate to `file:///`.
2.  **Save Page**: Save the page as `groot.html`.
3.  **Upload**: Commit and push the new `groot.html` to this repository.

## Future Improvements
- **Automated Sync**: A script could be added here to automatically generate and push this file.
- **Remote Access**: By enabling GitHub Pages, you can view this listing from anywhere (though links to local files will not work).
