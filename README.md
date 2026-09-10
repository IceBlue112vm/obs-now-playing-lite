<p align="center">
  <img src="assets/app-icon.png" width="160" alt="OBS Now Playing Lite">
</p>

<h1 align="center">OBS Now Playing Lite</h1>

<p align="center">
  A lightweight Windows app that displays your currently playing media in OBS.
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows-0078D4">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB">
  <img alt="OBS" src="https://img.shields.io/badge/OBS-WebSocket-302E31">
  <img alt="Release" src="https://img.shields.io/badge/release-v0.2.0-blue">
</p>

---

OBS Now Playing Lite automatically detects the title and artist of the media currently playing on Windows and displays them in OBS.

It is designed to reduce repetitive tasks such as copying track information, editing text sources, and repositioning them whenever the media changes.

## Features

- Automatically detects the current media title and artist on Windows
- Updates OBS text sources in real time through OBS WebSocket
- Allows manual editing of the detected title and artist
- Adjustable font size
- Automatically positions the overlay in the bottom-right corner
- Keeps the title and artist left-aligned
- Automatically truncates long text with `...`
- Saves settings between sessions
- Automatically reconnects to OBS using the saved password

## Requirements

- Windows 10 or Windows 11
- OBS Studio
- OBS WebSocket enabled

OBS WebSocket is included with modern versions of OBS Studio.

## Usage

### 1. Enable OBS WebSocket

In OBS Studio, open:

`Tools → WebSocket Server Settings`

Enable the WebSocket server and set a password.

### 2. Run OBS Now Playing Lite

Run:

`OBSNowPlayingLite.exe`

Windows SmartScreen may display a warning when the application is launched for the first time because the executable is not code-signed.

If this happens, select:

`More info → Run anyway`

### 3. Connect to OBS

Enter your OBS WebSocket password and click `연결` (Connect).

After a successful connection, the password and font size are saved locally.

On future launches, the application will automatically attempt to connect to OBS using the saved password.

### 4. Display the Overlay

Select the OBS scene where you want the media information to appear.

Then click:

`표시 시작` (Start Display)

The application automatically creates the following OBS text sources:

- `NowPlayingTitle`
- `NowPlayingArtist`

Although these are two separate OBS sources internally, they are managed together as a single Now Playing overlay.

To hide the overlay, click:

`표시 끄기` (Stop Display)

If you want to display it on another scene, stop the current display, switch to the desired scene in OBS, and start the display again.

## Overlay Behavior

The overlay is positioned automatically in the bottom-right corner of the OBS canvas.

The title is displayed above the artist, and both lines share the same left edge.

Whenever the media information or font size changes, the application recalculates the overlay position automatically.

If the title or artist is too long, the displayed text is shortened with `...` to prevent it from occupying too much of the screen.

The original media information is preserved internally.

## Settings

Settings are stored in:

`settings.json`

The file is created in the same directory as `OBSNowPlayingLite.exe`.

Currently stored settings include:

- OBS WebSocket password
- Font size

### Password Storage

The OBS WebSocket password is **not stored as plain text**.

OBS Now Playing Lite uses Windows DPAPI to encrypt the password for the current Windows user account.

Because of this, copying `settings.json` to another computer or Windows user account may prevent the saved password from being decrypted.

### Resetting Settings

Close OBS Now Playing Lite and delete:

`settings.json`

The application will recreate the file when settings are saved again.

Deleting the file resets both the saved OBS WebSocket password and font size.

## Troubleshooting

### Cannot connect to OBS

Make sure that:

- OBS Studio is running
- OBS WebSocket is enabled
- The WebSocket server is using the default port `4455`

You can check the WebSocket settings from:

`Tools → WebSocket Server Settings`

### Incorrect OBS WebSocket password

Open:

`Tools → WebSocket Server Settings`

in OBS and verify the password.

Then enter the correct password in OBS Now Playing Lite and connect again.

An incorrect password will not overwrite a previously saved valid password.

### Automatic connection no longer works

This may happen if:

- The OBS WebSocket password was changed
- `settings.json` was copied from another computer
- `settings.json` was created under another Windows user account

Close the application, delete `settings.json`, restart the application, and enter the OBS WebSocket password again.

### Windows SmartScreen blocks the application

OBS Now Playing Lite is currently distributed without a code-signing certificate.

Because of this, Windows SmartScreen may display a warning when launching a downloaded executable.

Select:

`More info → Run anyway`

to launch the application.

### Artist information is missing or incorrect

OBS Now Playing Lite displays the metadata provided by the current Windows media session.

Depending on the application or service playing the media, the artist field may be empty or may contain information such as a channel name instead of the actual artist name.

## Limitations

Version 0.2.0 focuses on keeping the application simple and quick to use.

The current version has the following limitations:

- Windows only
- Overlay position is fixed to the bottom-right corner
- Text alignment is fixed to left
- Title and artist use the same font size
- Long text is truncated instead of scrolling
- Media information depends on metadata provided by the Windows media session
- Playback controls are not supported
- Album artwork, lyrics, and playback progress are not supported

## Development

Built with:

- Python 3.12
- Tkinter
- Windows Runtime Media Control
- OBS WebSocket
- obsws-python
- PyInstaller

### Build

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the build dependencies:

```powershell
python -m pip install -r requirements-build.txt
```

Build the application using the included build script:

```powershell
.\build.ps1
```

The build script:

- Cleans previous build outputs
- Builds the executable using `OBSNowPlayingLite.spec`
- Creates a release package containing the executable and README
- Generates the final ZIP file in the `dist` directory

You can optionally specify a version for the package name:

```powershell
.\build.ps1 -Version "0.2.0"
```

Build outputs are created in:

```text
dist/
├── OBSNowPlayingLite.exe
├── OBSNowPlayingLite-v0.2.0/
└── OBSNowPlayingLite-v0.2.0.zip
```

The generated ZIP file is the package intended for distribution.
