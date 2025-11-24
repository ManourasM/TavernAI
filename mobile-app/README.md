# Tavern PWA (Progressive Web App)

A unified Progressive Web App for the Tavern Ordering System with authentication, menu setup via OCR, multi-endpoint support, and notifications.

**✨ No app store needed! Users just visit a URL and click "Add to Home Screen"**

## Features

### ✅ Implemented
- **User Authentication System**
  - Role-based access (Admin, Waiter, Kitchen, Grill, Drinks)
  - Persistent login with Capacitor Preferences
  - Default demo users for testing

- **Menu Setup with OCR**
  - Camera integration for menu photo capture
  - Upload existing images
  - OCR text extraction using Tesseract.js (Greek language support)
  - Automatic menu item parsing

- **State Management**
  - Zustand for global state
  - Persistent storage with Capacitor Preferences
  - Auth, Menu, and Notification stores

- **HTML5 Camera & File Upload**
  - Camera access via HTML5 input
  - File upload from gallery
  - Works on all modern browsers

- **Web Notifications API**
  - In-app notifications (works on Android)
  - Visual and sound alerts
  - Notification history

- **Progressive Web App (PWA)**
  - Offline functionality with service workers
  - Installable on mobile devices (Add to Home Screen)
  - App manifest for native-like experience
  - Works on Android and iOS
  - No app store needed!

### 🚧 To Be Implemented
- Menu Editor component (preview and edit extracted items)
- HomePage with multi-tab navigation
- AdminPage for user and endpoint management
- WebSocket integration for real-time updates
- Notification triggers when orders are ready
- Endpoint assignment for menu items

## Installation

```bash
cd mobile-app
npm install
```

## Development

### Web Development Mode
```bash
npm run dev
```
Access at: http://localhost:5177

### Build for Production
```bash
npm run build
```

### Android Development
```bash
# First build
npm run build

# Sync with Android
npx cap add android
npm run android

# This opens Android Studio
# Run the app from Android Studio
```

### iOS Development
```bash
# First build
npm run build

# Sync with iOS
npx cap add ios
npm run ios

# This opens Xcode
# Run the app from Xcode
```

## Project Structure

```
mobile-app/
├── src/
│   ├── components/          # Reusable components
│   │   ├── MenuOCR.jsx     # OCR processing component
│   │   ├── MenuEditor.jsx  # Menu editing interface
│   │   └── ...
│   ├── pages/              # Main pages
│   │   ├── LoginPage.jsx   # Authentication
│   │   ├── SetupPage.jsx   # Menu setup wizard
│   │   ├── HomePage.jsx    # Main app interface
│   │   └── AdminPage.jsx   # Admin panel
│   ├── store/              # State management
│   │   ├── authStore.js    # Authentication state
│   │   ├── menuStore.js    # Menu data state
│   │   └── notificationStore.js  # Notifications
│   ├── App.jsx             # Main app component
│   ├── main.jsx            # Entry point
│   └── index.css           # Global styles
├── public/                 # Static assets
├── capacitor.config.json   # Capacitor configuration
├── vite.config.js          # Vite + PWA configuration
└── package.json
```

## Default Users

For testing, use these credentials:

| Role    | Username | Password    |
|---------|----------|-------------|
| Admin   | admin    | admin123    |
| Waiter  | waiter   | waiter123   |
| Kitchen | kitchen  | kitchen123  |
| Grill   | grill    | grill123    |
| Drinks  | drinks   | drinks123   |

## Workflow

### 1. Login
- User logs in with credentials
- Role determines accessible features

### 2. Menu Setup (Admin Only)
- Take photo of physical menu or upload image
- OCR extracts text (Greek language support)
- AI parses items and prices
- Preview and edit extracted menu
- Assign items to endpoints (kitchen/grill/drinks)
- Save menu

### 3. Daily Operations
- **Waiter**: Takes orders, views all endpoints
- **Kitchen/Grill/Drinks**: Views only their endpoint
- **Admin**: Full access to all features

### 4. Notifications
- Receive alerts when orders are ready
- Mute/unmute option
- Sound and vibration controls

## Technologies

- **React 19** - UI framework
- **Vite** - Build tool
- **Capacitor 6** - Native mobile wrapper
- **Zustand** - State management
- **React Router** - Navigation
- **Tesseract.js** - OCR engine
- **PWA** - Offline support

## Next Steps

1. Complete MenuEditor component
2. Build HomePage with tabbed interface
3. Implement AdminPage for management
4. Add WebSocket integration
5. Connect notification triggers
6. Test on physical devices
7. Add AI-powered menu parsing (optional)

## Notes

- OCR currently supports Greek language (ell)
- Menu data stored locally with Capacitor Preferences
- Can sync with backend API (to be implemented)
- Works offline after initial setup
- No app store distribution needed (can install via APK/IPA)

