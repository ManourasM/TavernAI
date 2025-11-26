# Quick Start Guide

Get the PWA running in 5 minutes!

**✨ This is now a PWA (Progressive Web App) - no Android Studio or Xcode needed!**

## 🚀 Development Mode

```bash
# 1. Navigate to mobile-app directory
cd mobile-app

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev

# 4. Open in browser
# Visit: http://localhost:5177
```

**Note:** The server will show both Local and Network URLs. Use the Network URL to connect from your phone!

**📱 To test on your phone:** See `MOBILE_CONNECTION_GUIDE.md` for detailed instructions.

### Test the App

1. **Login Screen**
   - Try: `admin` / `admin123`
   - Or: `waiter` / `waiter123`

2. **Setup Screen** (Admin only)
   - Click "Skip setup" for now (camera won't work in browser)
   - Or upload a menu image to test OCR

3. **Home Screen**
   - See multi-tab navigation
   - Test notification mute toggle
   - Access admin panel (admin only)

## 📱 Test on Mobile Device

### Option 1: Test Locally (Same WiFi Network)

**📖 See `MOBILE_CONNECTION_GUIDE.md` for detailed step-by-step instructions!**

**Quick version:**

1. **Start dev server**:
   ```bash
   npm run dev
   ```

2. **Copy the Network URL** from the terminal output:
   ```
   ➜  Network: http://192.168.1.100:5177/
   ```

3. **Open on your phone** and visit that URL

4. **Allow firewall** if Windows asks

5. **Test features!**
   - Use "📁 Upload Image" for menu setup (works on all devices)
   - Camera may require HTTPS (deploy to Netlify for full camera support)

### Option 2: Deploy and Test (Recommended)

See `PWA_DEPLOYMENT.md` for deployment to Netlify/Vercel (free and easy!)

Once deployed, users can:
1. Visit your URL
2. Click "Add to Home Screen"
3. Use like a native app!

## 🧪 Testing Features

### Authentication
- **Admin**: Full access to all features
- **Waiter**: Access to waiter interface
- **Kitchen/Grill/Drinks**: Access to their station only

### Menu Setup (Admin Only)
1. Login as admin
2. Take photo or upload image of menu
3. Wait for OCR processing (Greek language supported)
4. Edit extracted items
5. Save menu

### Notifications
- Toggle mute/unmute from home screen
- Notifications will trigger when orders are ready (to be implemented)

## 🐛 Troubleshooting

### "npm install" fails
```bash
# Clear cache and try again
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Port 5177 already in use
```bash
# Kill the process or change port in vite.config.js
# Windows:
netstat -ano | findstr :5177
taskkill /PID <PID> /F

# Mac/Linux:
lsof -ti:5177 | xargs kill -9
```

### Camera not working
- Camera requires HTTPS (or localhost for testing)
- Grant camera permissions when prompted
- Alternatively, use "Upload Image" option

### "Add to Home Screen" not showing
- PWA features require HTTPS in production
- Test locally with `npm run build && npm run preview`
- Or deploy to Netlify/Vercel (automatic HTTPS)

## 📖 Next Steps

1. **Read full documentation**
   - `README.md` - Feature overview
   - `SETUP_GUIDE.md` - Detailed setup
   - `IMPLEMENTATION_STATUS.md` - What's done/remaining

2. **Customize the app**
   - Update app name in `capacitor.config.json`
   - Change colors in `src/index.css`
   - Add your logo

3. **Integrate with backend**
   - Update backend URL in `.env`
   - Test WebSocket connection
   - Sync menu data

4. **Build for production**
   - Follow `SETUP_GUIDE.md` for APK/IPA builds
   - Test on physical devices
   - Distribute to users

## 💡 Tips

- **Development**: Use `npm run dev` for fastest iteration
- **Testing**: Test on your phone via local network (see above)
- **Production**: Deploy to Netlify/Vercel for free HTTPS hosting
- **Camera**: Both "Take Photo" and "Upload Image" options work
- **Offline**: PWA works offline after first visit!

## 🆘 Need Help?

Check the documentation:
- `README.md` - Overview
- `SETUP_GUIDE.md` - Detailed instructions
- `IMPLEMENTATION_STATUS.md` - Current status

## 🎯 Default Credentials

| Role    | Username | Password    |
|---------|----------|-------------|
| Admin   | admin    | admin123    |
| Waiter  | waiter   | waiter123   |
| Kitchen | kitchen  | kitchen123  |
| Grill   | grill    | grill123    |
| Drinks  | drinks   | drinks123   |

Happy coding! 🎉

