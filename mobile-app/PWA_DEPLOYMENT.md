# PWA Deployment Guide

Simple guide to deploy your Tavern PWA so users can install it on their phones.

## 🎯 What Users Will Do

1. Visit your website: `https://yourtavern.com`
2. Browser shows: "Add Tavern to Home Screen"
3. Click "Add"
4. **Done!** App icon appears on home screen

**No APK files, no "Unknown Sources", no complexity!**

---

## 📋 Prerequisites

You need:
1. A web server (any hosting provider)
2. An HTTPS certificate (free with Let's Encrypt)
3. A domain name (optional but recommended)

---

## 🚀 Deployment Steps

### Option 1: Deploy to Netlify (Easiest - FREE)

**Perfect for beginners!**

1. **Create account** at [netlify.com](https://netlify.com)

2. **Build your app**:
   ```bash
   cd mobile-app
   npm install
   npm run build
   ```

3. **Deploy**:
   - Drag the `dist` folder to Netlify
   - Or connect your GitHub repo
   - Netlify automatically provides HTTPS!

4. **Share the URL** with users:
   - Example: `https://your-tavern.netlify.app`

**That's it!** Users can now install your PWA.

---

### Option 2: Deploy to Vercel (Also Easy - FREE)

1. **Create account** at [vercel.com](https://vercel.com)

2. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

3. **Build and deploy**:
   ```bash
   cd mobile-app
   npm run build
   vercel --prod
   ```

4. **Share the URL** with users

---

### Option 3: Deploy to Your Own Server

**Requirements:**
- Web server (Apache, Nginx, etc.)
- HTTPS certificate (use Let's Encrypt - free)

**Steps:**

1. **Build the app**:
   ```bash
   cd mobile-app
   npm install
   npm run build
   ```

2. **Upload `dist` folder** to your server:
   ```bash
   # Example with SCP
   scp -r dist/* user@yourserver.com:/var/www/html/
   ```

3. **Configure web server** to serve the files

4. **Ensure HTTPS** is enabled (required for PWA)

---

## 📱 How Users Install the PWA

### On Android (Chrome/Edge)

1. Visit your URL in Chrome
2. Tap the menu (⋮)
3. Tap "Add to Home screen"
4. Confirm
5. **Done!** App appears on home screen

**Or:** Chrome will show a banner: "Add Tavern to Home Screen"

### On iOS (Safari)

1. Visit your URL in Safari
2. Tap the Share button (□↑)
3. Scroll and tap "Add to Home Screen"
4. Confirm
5. **Done!** App appears on home screen

### On Desktop

1. Visit your URL in Chrome/Edge
2. Look for install icon in address bar
3. Click "Install"
4. **Done!** App opens in its own window

---

## ✅ Testing Before Deployment

### Test Locally

```bash
cd mobile-app
npm run build
npm run preview
```

Visit: `http://localhost:4173`

### Test PWA Features

1. Open Chrome DevTools (F12)
2. Go to "Application" tab
3. Check:
   - ✅ Manifest is valid
   - ✅ Service Worker is registered
   - ✅ Icons are present

---

## 🎨 Customization Before Deployment

### 1. Update App Name

Edit `mobile-app/vite.config.js`:
```javascript
manifest: {
  name: 'Your Tavern Name',
  short_name: 'Tavern',
  // ...
}
```

### 2. Add App Icons

Replace these files in `mobile-app/public/`:
- `pwa-192x192.png` (192x192 pixels)
- `pwa-512x512.png` (512x512 pixels)

**Tip:** Use [favicon.io](https://favicon.io) to generate icons

### 3. Update Theme Color

Edit `mobile-app/vite.config.js`:
```javascript
manifest: {
  theme_color: '#667eea', // Change this
  // ...
}
```

---

## 🔧 Connecting to Backend

If your backend is on a different server:

1. **Update backend URL** in `.env`:
   ```
   VITE_BACKEND_URL=https://api.yourtavern.com
   VITE_BACKEND_WS_URL=wss://api.yourtavern.com
   ```

2. **Enable CORS** on your backend to allow requests from your PWA domain

3. **Rebuild**:
   ```bash
   npm run build
   ```

---

## 📊 Monitoring

After deployment, you can track:
- How many users installed the PWA
- Usage analytics
- Error reports

Use tools like:
- Google Analytics
- Sentry (for error tracking)
- Lighthouse (for PWA score)

---

## 🆘 Troubleshooting

### "Add to Home Screen" doesn't appear

**Check:**
- ✅ Site is served over HTTPS
- ✅ Manifest file is valid
- ✅ Service worker is registered
- ✅ Icons are present (192x192 and 512x512)

**Test with Lighthouse:**
```bash
# In Chrome DevTools
1. Open DevTools (F12)
2. Go to "Lighthouse" tab
3. Select "Progressive Web App"
4. Click "Generate report"
```

### Camera doesn't work

- Camera requires HTTPS (works on localhost for testing)
- User must grant camera permissions

### Notifications don't work on iOS

- iOS Safari has limited notification support
- In-app notifications still work
- Sound alerts work

---

## 🎉 Success!

Once deployed, share your URL with users:

**Example message to users:**
> Visit https://yourtavern.com on your phone and click "Add to Home Screen" to install the Tavern app!

That's it! No app stores, no complicated installation process.

---

## 📚 Additional Resources

- [PWA Documentation](https://web.dev/progressive-web-apps/)
- [Netlify Docs](https://docs.netlify.com/)
- [Vercel Docs](https://vercel.com/docs)
- [Let's Encrypt](https://letsencrypt.org/) (Free HTTPS)

