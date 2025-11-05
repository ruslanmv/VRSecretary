# VRSecretaryGame

VRSecretary AI-powered VR game project - Complete Tutorial.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Project Setup](#project-setup)
4. [Import Avatar Model](#import-avatar-model)
5. [Setup VR Environment](#setup-vr-environment)
6. [Create Avatar Blueprint](#create-avatar-blueprint)
7. [Setup Player Controllers](#setup-player-controllers)
8. [Auto VR Detection](#auto-vr-detection)
9. [Backend Integration](#backend-integration)
10. [Testing](#testing)
11. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Open Project (Windows)

**This project was created from WSL but runs in Windows!**

- Open Windows File Explorer
- Navigate to project folder (path shown when script completed)
- Double-click `VRSecretaryGame.uproject`
- Wait for initial C++ compilation (5-15 minutes first time)

### 2. Import Scifi Girl Model

**Download:**
- URL: https://sketchfab.com/3d-models/scifi-girl-v01-96340701c2ed4d37851c7d9109eee9c0
- Format: **GLB**
- Texture Size: **4K** (88MB)

**Import:**
1. In Unreal, open Content Browser
2. Navigate to: `Content/VRSecretaryGame/Characters/ScifiGirl/Meshes/`
3. Click "Import"
4. Select downloaded GLB file
5. Import Settings:
   - ✓ Skeletal Mesh
   - ✓ Import Materials
   - ✓ Import Textures
   - Skeleton: Create New
6. Click "Import All"
7. Wait 30-60 seconds

### 3. Test

**VR Mode:**
- Connect VR headset
- Click "VR Preview" button (headset icon)

**Desktop Mode:**
- Click "Play" button
- Use WASD + Mouse

---

## Prerequisites

### Required Software

- **Unreal Engine 5.3+** - [Download](https://www.unrealengine.com/download)
- **Visual Studio 2022** (Windows) - [Download](https://visualstudio.microsoft.com/)
  - Workload: "Game Development with C++"
- **Git** - [Download](https://git-scm.com/)
- **Python 3.11** (for backend) - [Download](https://www.python.org/)

### Required Hardware

- **PC:** Windows 10/11, 16GB RAM, GTX 1060+
- **VR Headset:** Oculus Quest 2/3 or SteamVR compatible
- **USB-C cable** or **Air Link** for Quest

### Optional (for AI features)

- **Ollama** - [Download](https://ollama.ai/)
- **Chatterbox TTS** - Installed via VRSecretary backend

---

## Project Setup

### Project Structure (Created Automatically)
```
VRSecretaryGame/
├── Content/
│   └── VRSecretaryGame/
│       ├── Characters/
│       │   └── ScifiGirl/         # Import model here
│       │       ├── Meshes/
│       │       ├── Materials/
│       │       ├── Textures/
│       │       └── Animations/
│       ├── Maps/                   # Levels
│       ├── Blueprints/
│       │   ├── Core/               # Game mode
│       │   ├── VR/                 # VR player
│       │   └── Desktop/            # Desktop player
│       ├── UI/
│       │   └── Widgets/            # UI elements
│       └── Audio/
│           └── VoiceLines/
├── Plugins/
│   └── VRSecretary/                # AI plugin (pre-installed)
├── Config/                         # Project settings
└── Source/                         # C++ code
```

### Configuration Files

Already configured:

- **DefaultEngine.ini** - VR settings, rendering
- **DefaultInput.ini** - Controls (VR controllers, keyboard/mouse)
- **DefaultGame.ini** - Project metadata
- **VRSecretary Settings** - Backend URL, mode selection

---

## Import Avatar Model

### Step 1: Download Model

1. Visit: https://sketchfab.com/3d-models/scifi-girl-v01-96340701c2ed4d37851c7d9109eee9c0
2. Click "Download 3D Model"
3. Select: **GLB format**
4. Texture Resolution: **4K** (88MB recommended)
5. Click "Download"
6. Save to Desktop or Downloads

### Step 2: Import into Unreal

1. **Open Unreal Editor** with your project
2. **Navigate in Content Browser:**
   - `Content/VRSecretaryGame/Characters/ScifiGirl/Meshes/`
3. **Click "Import" button**
4. **Select downloaded GLB file**
5. **Configure Import Settings:**
```
Mesh:
✓ Skeletal Mesh              (REQUIRED for animations)
✓ Import Mesh
✓ Import Normals
☐ Import Tangents             (auto-generate)

Materials:
✓ Import Materials
✓ Import Textures
Material Import Method: Create New Materials

Skeleton:
Skeleton: [Create New]

Transform:
Import Uniform Scale: 1.0
```

6. **Click "Import All"**
7. **Wait for import** (30-60 seconds)

### Step 3: Verify Import

You should now see:

- **SK_ScifiGirl** - Skeletal Mesh
- **SK_ScifiGirl_Skeleton** - Skeleton asset
- **SK_ScifiGirl_PhysicsAsset** - Physics
- **Materials/** folder - Material instances
- **Textures/** folder - Texture files

**Test the model:**
- Double-click `SK_ScifiGirl`
- Model should display correctly with textures
- No pink "missing texture" errors

---

## Setup VR Environment

### Lighting & Sky

Already set up in config, but to customize:

1. **Directional Light:**
   - Location: `(0, 0, 500)`
   - Rotation: `(-45, 0, 0)`
   - Intensity: `5.0`

2. **Sky Atmosphere:**
   - Adds realistic sky/clouds

3. **Sky Light:**
   - ✓ Real Time Capture
   - Intensity: `1.0`

### Floor & Walls

Create a simple office environment:

1. **Floor:**
   - Place Actors → Basic → Plane
   - Scale: `(10, 10, 1)`
   - Material: `M_Concrete_Tiles` (Starter Content)

2. **Walls (optional):**
   - Use Cubes scaled thin
   - Position around perimeter

### Player Start

- Position: `(0, 0, 0)` (on floor)
- Rotation: `(0, 0, 0)` (facing forward)

---

## Create Avatar Blueprint

### What Was Created Automatically

The script created the folder structure. Now we'll create the Blueprint manually.

### Step 1: Create Blueprint

1. **Navigate to:**
   - `Content/VRSecretaryGame/Characters/`
2. **Right-click → Blueprint Class → Actor**
3. **Name:** `BP_SecretaryAvatar`
4. **Open it** (double-click)

### Step 2: Add Components

**In the Components panel:**

1. **Add Skeletal Mesh:**
   - Add Component → Skeletal Mesh
   - Rename: `AvatarMesh`
   - Details:
     - Skeletal Mesh: `SK_ScifiGirl`
     - Location: `(0, 0, -90)` (adjust so feet touch ground)
     - Rotation: `(0, 0, -90)` (face forward)

2. **Add Audio Component:**
   - Add Component → Audio
   - Rename: `VoiceAudio`
   - Parent to: `AvatarMesh` (drag onto it)
   - Location: `(0, 0, 160)` (head height)

3. **Add Text Render (Subtitles):**
   - Add Component → Text Render
   - Rename: `SubtitleText`
   - Parent to: `AvatarMesh`
   - Location: `(0, 0, 200)` (above head)
   - Details:
     - Text: "Hello! I'm Ailey."
     - Horizontal Alignment: Center
     - Vertical Alignment: Text Top
     - World Size: 24
     - Text Color: White

### Step 3: Place in Level

1. **Drag** `BP_SecretaryAvatar` from Content Browser into viewport
2. **Position:** `(300, 0, 0)` (3 meters in front of player)
3. **Rotation:** `(0, 0, 180)` (facing toward player spawn)

### Step 4: Compile & Save

- Click **Compile** (top toolbar)
- Click **Save**

---

## Setup Player Controllers

### VR Player (Already Exists from Template)

The VR Template includes a functional VR pawn. We'll customize it:

1. **Find:** `Content/VRTemplate/Blueprints/VRPawn`
2. **Duplicate it:**
   - Right-click → Duplicate
   - Move to: `Content/VRSecretaryGame/Blueprints/VR/`
   - Rename: `BP_VRPawn`

3. **Open BP_VRPawn**

4. **Adjust Camera Height:**
   - Select Camera component
   - Location Z: `160` (average eye height)

5. **Add Gaze Interaction (Event Graph):**
```
Event Tick
├─> Get Actor Location (Camera)
├─> Get Forward Vector (Camera)
│   └─> Multiply (1000)
├─> Line Trace By Channel
│   ├─ Start: Camera Location
│   ├─ End: Camera Location + Forward * 1000
│   ├─ Trace Channel: Visibility
│   └─> Branch (Hit?)
│       ├─ True:
│       │   └─> Cast to BP_SecretaryAvatar
│       │       └─> Store: CurrentLookTarget
│       └─ False:
│           └─> Clear: CurrentLookTarget
```

6. **Add Talk Input:**
```
Input Action "TriggerRight" Pressed
└─> Is Valid? (CurrentLookTarget)
    └─ True:
        └─> Print String: "Talking to Ailey"
        └─> (Future: VRSecretary API call)
```

7. **Compile & Save**

### Desktop Player (New)

1. **Navigate to:** `Content/VRSecretaryGame/Blueprints/Desktop/`
2. **Create Blueprint Class → Character**
3. **Name:** `BP_DesktopPlayer`
4. **Open it**

5. **Add Camera:**
   - Add Component → Camera
   - Location: `(0, 0, 64)` (eye level)

6. **Setup Movement (Event Graph):**
```
Event BeginPlay
└─> Set Show Mouse Cursor: True

Input Axis "MoveForward"
└─> Add Movement Input
    └─ Direction: Get Actor Forward Vector

Input Axis "MoveRight"
└─> Add Movement Input
    └─ Direction: Get Actor Right Vector

Input Axis "Turn"
└─> Add Controller Yaw Input

Input Axis "LookUp"
└─> Add Controller Pitch Input
```

7. **Add Interaction:**
```
Input Action "Interact" (E Key) Pressed
└─> Line Trace from Camera (500 units)
    └─> Hit BP_SecretaryAvatar?
        └─ True:
            └─> Print String: "Interacting with Ailey"
```

8. **Compile & Save**

---

## Auto VR Detection

### Create Game Mode

1. **Navigate to:** `Content/VRSecretaryGame/Blueprints/Core/`
2. **Create Blueprint Class → Game Mode Base**
3. **Name:** `BP_GameMode`
4. **Open it**

5. **Auto-Detection Logic (Event Graph):**
```
Event BeginPlay
└─> Is Head Mounted Display Enabled?
    └─> Branch
        ├─ True (VR Detected):
        │   ├─> Print String: "VR Mode Active" (Green)
        │   └─> Set Default Pawn Class: BP_VRPawn
        │
        └─ False (No VR):
            ├─> Print String: "Desktop Mode Active" (Yellow)
            └─> Set Default Pawn Class: BP_DesktopPlayer
```

6. **Compile & Save**

### Set Game Mode in Level

1. **Open your level** (e.g., `VR_Office`)
2. **Window → World Settings**
3. **Game Mode Override:** `BP_GameMode`
4. **Save Level**

---

## Backend Integration

### Prerequisites

Before connecting to AI backend, you need:

1. **VRSecretary Backend Running**
2. **Ollama** (local LLM)
3. **Chatterbox** (TTS)

### Setup Backend (WSL/Ubuntu)
```bash
# From WSL terminal
cd /path/to/VRSecretary

# Install dependencies
make install

# Start services (3 separate terminals)

# Terminal 1: Ollama
ollama serve

# Terminal 2: Chatterbox
chatterbox-server --port 4123

# Terminal 3: Gateway
make run-gateway
```

### Test Backend
```bash
# Check health
curl http://localhost:8000/health

# Test chat endpoint
curl -X POST http://localhost:8000/api/vr_chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","user_text":"Hello!"}'
```

### Plugin Configuration (Already Done)

The VRSecretary plugin is already installed and configured:

- **Plugin Location:** `Plugins/VRSecretary/`
- **Settings:** Edit → Project Settings → Plugins → VRSecretary
- **Gateway URL:** `http://localhost:8000`
- **Backend Mode:** Gateway (Ollama)

### Add Component to Avatar

1. **Open** `BP_SecretaryAvatar`
2. **Add Component:** VRSecretary Component
3. **Configure (Details panel):**
   - Gateway URL: (uses project settings)
   - Backend Mode: (uses project settings)

### Bind Events (Event Graph)
```
Event BeginPlay
├─> Get VRSecretary Component
    │
    ├─> Assign On Assistant Response
    │   └─> (Event) On Assistant Response
    │       ├─> Set Text (SubtitleText): Assistant Text
    │       └─> Play Audio: Audio Base64 (decode first)
    │
    └─> Assign On Error
        └─> (Event) On Error
            └─> Print String: Error Message (Red)
```

### Update Player Interaction

**In BP_VRPawn or BP_DesktopPlayer:**
```
On Interact/Talk Button
└─> Get VRSecretary Component (from Avatar)
    └─> Send User Text With Default Config
        └─ User Text: "Hello Ailey, how are you?"
```

---

## Testing

### Test Desktop Mode

1. **Click Play** (standard play button)
2. **Controls:**
   - WASD: Move
   - Mouse: Look
   - E: Interact (when near avatar)
3. **Expected:**
   - "Desktop Mode Active" message
   - Can walk around
   - Avatar is visible

### Test VR Mode

1. **Connect VR headset** (Quest via Link/Air Link or SteamVR)
2. **Click VR Preview** (headset icon)
3. **Put on headset**
4. **Expected:**
   - "VR Mode Active" message
   - Room-scale tracking works
   - Controllers tracked
   - Look at avatar → interaction prompt

### Test Backend (Full Pipeline)

1. **Start all backend services** (Ollama, Chatterbox, Gateway)
2. **Test manually first:**
```bash
curl -X POST http://localhost:8000/api/vr_chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","user_text":"Hi!"}'
```

3. **Launch game (VR or Desktop)**
4. **Interact with avatar**
5. **Expected:**
   - Subtitle appears with AI response
   - Audio plays (if decoder working)
   - Logs show success

---

## Troubleshooting

### Common Issues

#### "Cannot open project"

**Problem:** Double-clicking .uproject does nothing

**Solution:**
- Right-click .uproject → "Switch Unreal Engine Version"
- Select 5.3 or your installed version
- Right-click → "Generate Visual Studio project files"
- Try opening again

#### "Compilation failed"

**Problem:** C++ compilation errors on first open

**Solution:**
- Ensure Visual Studio 2022 installed with "Game Development with C++"
- Close Unreal, open .sln file in Visual Studio
- Build → Build Solution
- Then open .uproject

#### "Model is pink/missing textures"

**Problem:** Avatar has pink materials

**Solution:**
- Reimport GLB with "Import Textures" checked
- Check textures are in Textures folder
- Verify material assignments in SK_ScifiGirl

#### "VR not detected"

**Problem:** Always starts in Desktop mode

**Solution:**
- Check SteamVR or Oculus software running
- Enable VR in Project Settings → VR
- Use "VR Preview" button, not regular "Play"

#### "Backend connection failed"

**Problem:** "Failed to connect to backend" error

**Solution:**
- Verify backend running: `curl http://localhost:8000/health`
- Check firewall settings (allow port 8000)
- Verify Gateway URL in Project Settings
- Check backend logs for errors

#### "No audio playback"

**Problem:** Text appears but no voice

**Solution:**
- Check Chatterbox running: `curl http://localhost:4123/health` (if available)
- Install Runtime Audio Importer plugin (for base64 audio decoding)
- Verify audio component attached to avatar
- Check VoiceAudio component settings

---

## WSL Notes

This project was created from WSL but runs in Windows:

- **Unreal Engine:** Runs in Windows
- **Backend Services:** Can run in WSL (Python, Ollama, etc.)
- **Files:** Accessible from both environments
- **Paths:**
  - Windows: `C:\UnrealProjects\VRSecretaryGame\`
  - WSL: `/mnt/c/UnrealProjects/VRSecretaryGame/`

**Workflow:**
1. Develop in Unreal (Windows)
2. Backend in WSL terminal
3. Git operations from either

---

## Next Steps

### Phase 1: Basic Functionality
- [ ] Import Scifi Girl model
- [ ] Test VR mode
- [ ] Test Desktop mode
- [ ] Verify auto-detection

### Phase 2: Backend Integration
- [ ] Setup backend services
- [ ] Test `/api/vr_chat` endpoint
- [ ] Add VRSecretary component
- [ ] Test full conversation

### Phase 3: Polish
- [ ] Add animations to avatar
- [ ] Improve lighting
- [ ] Add hand interactions (VR)
- [ ] Create proper UI for text input

### Phase 4: Advanced
- [ ] Lip-sync animation
- [ ] Gesture recognition
- [ ] Multiple conversation topics
- [ ] Quest optimization

---

## Additional Resources

- **VRSecretary Main Docs:** `../docs/`
- **Unreal VR Docs:** https://docs.unrealengine.com/5.3/en-US/developing-for-vr-in-unreal-engine/
- **Oculus Developer:** https://developer.oculus.com/
- **Sketchfab (Models):** https://sketchfab.com/

---

## Credits

- **VRSecretary Project:** Ruslan Magana Vsevolodovna
- **Scifi Girl Model:** patrix (CC BY-NC-SA 4.0)
- **Unreal Engine:** Epic Games
- **Tutorial:** Auto-generated by create-project-wsl.sh

---

## License

- **Project Code:** Apache 2.0
- **Scifi Girl Model:** CC BY-NC-SA 4.0 (non-commercial use only)

For commercial use, replace the avatar with a marketplace asset or commission custom model.

---

**🎮 Ready to start? Follow the Quick Start section above!**
