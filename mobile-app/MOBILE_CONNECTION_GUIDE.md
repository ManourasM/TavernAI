# 📱 Mobile Connection Guide

## How to Connect Your Phone to the Development Server

### ✅ Prerequisites

1. **Same WiFi Network**: Your computer and phone must be on the same WiFi network
2. **Firewall**: Windows Firewall may need to allow Node.js connections

---

## 🚀 Step-by-Step Instructions

### Step 1: Find Your Computer's IP Address

**On Windows:**

1. Open PowerShell or Command Prompt
2. Type: `ipconfig`
3. Look for "IPv4 Address" under your WiFi adapter
4. Example: `192.168.1.100`

**Quick PowerShell command:**
```powershell
(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi").IPAddress
```

---

### Step 2: Start the Development Server

In the `mobile-app` directory:

```bash
npm run dev
```

You should see output like:
```
  ➜  Local:   http://localhost:5177/
  ➜  Network: http://192.168.1.100:5177/
```

**Copy the Network URL!** (e.g., `http://192.168.1.100:5177`)

---

### Step 3: Allow Firewall Access (Windows)

When you first run `npm run dev`, Windows Firewall may show a popup:

**"Windows Defender Firewall has blocked some features of Node.js"**

✅ **Check both boxes:**
- Private networks (home or work)
- Public networks

✅ **Click "Allow access"**

**If you missed the popup:**

1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Find "Node.js" in the list
4. Check both "Private" and "Public"
5. Click OK

---

### Step 4: Connect from Your Phone

1. **Open your phone's browser** (Chrome, Safari, etc.)
2. **Type the Network URL**: `http://YOUR_IP:5177`
   - Example: `http://192.168.1.100:5177`
3. **Press Enter**

You should see the Tavern login page! 🎉

---

## 🧪 Testing Camera on Mobile

### Important Notes:

1. **Camera requires HTTPS in production**
   - On localhost/local network, camera may not work in all browsers
   - **Solution**: Use the "Upload Image" button instead
   - Or deploy to Netlify/Vercel for HTTPS

2. **File Upload always works**
   - The "📁 Upload Image" button works on all devices
   - Opens your phone's gallery/camera
   - No HTTPS required

---

## 🔧 Troubleshooting

### Problem: "Can't connect" or "Site can't be reached"

**Solution 1: Check WiFi**
- Ensure phone and computer are on the **same WiFi network**
- Not on guest network or different network

**Solution 2: Check Firewall**
- Make sure Windows Firewall allows Node.js
- See Step 3 above

**Solution 3: Try Different IP**
- Your computer may have multiple network adapters
- Run `ipconfig` and try different IPv4 addresses
- Look for addresses starting with `192.168.x.x` or `10.x.x.x`

**Solution 4: Restart Dev Server**
- Stop the server (Ctrl+C)
- Run `npm run dev` again
- Check the "Network" URL in the output

**Solution 5: Check Port**
- Make sure you're using port `5177`
- Example: `http://192.168.1.100:5177`

---

### Problem: Camera doesn't work on phone

**Solution:**
- Use the **"📁 Upload Image"** button instead
- This opens your phone's gallery/camera
- Works on all devices without HTTPS

**For full camera support:**
- Deploy to Netlify/Vercel (free HTTPS)
- See `PWA_DEPLOYMENT.md`

---

### Problem: "Network" URL not showing

**Solution:**
- Make sure you're running `npm run dev` (not just `vite`)
- The `--host` flag is now included in the script
- You should see both Local and Network URLs

---

## 📱 Testing on Mobile

### What to Test:

1. **Login**
   - Username: `admin`
   - Password: `admin123`

2. **Menu Setup**
   - Click "Setup Menu"
   - Try "📁 Upload Image" (works on all devices)
   - Upload a photo of a menu
   - Watch OCR extract text
   - Edit menu items
   - Save

3. **Navigation**
   - Test tab switching
   - Test notifications toggle
   - Test logout

4. **Add to Home Screen**
   - In Chrome (Android): Menu → "Add to Home Screen"
   - In Safari (iOS): Share → "Add to Home Screen"

---

## 🌐 Alternative: Deploy for Easy Access

Instead of connecting via IP, you can deploy to get a permanent URL:

### Netlify (Easiest - Free)

1. Build the app:
   ```bash
   npm run build
   ```

2. Go to [netlify.com](https://netlify.com)

3. Drag the `dist` folder

4. Get your URL: `https://your-tavern.netlify.app`

5. Share with anyone!

**Benefits:**
- ✅ HTTPS (camera works)
- ✅ Permanent URL
- ✅ Works from anywhere
- ✅ Free

See `PWA_DEPLOYMENT.md` for detailed instructions.

---

## 📊 Quick Reference

| What | Command | URL |
|------|---------|-----|
| **Find IP** | `ipconfig` | Look for IPv4 Address |
| **Start Server** | `npm run dev` | Check "Network" URL |
| **Phone Browser** | Open browser | `http://YOUR_IP:5177` |
| **Allow Firewall** | Windows popup | Check both boxes |

---

## ✅ Success Checklist

- [ ] Found computer's IP address
- [ ] Started dev server with `npm run dev`
- [ ] Allowed Node.js through Windows Firewall
- [ ] Phone and computer on same WiFi
- [ ] Opened `http://YOUR_IP:5177` on phone
- [ ] Can see login page
- [ ] Can login and navigate
- [ ] Can upload images (file upload works!)

---

## 🎉 You're Connected!

Once you see the login page on your phone, you're all set!

**Next Steps:**
- Test all features on mobile
- Try "Add to Home Screen"
- Consider deploying to Netlify for permanent access

**Need Help?**
- Check the troubleshooting section above
- Make sure firewall is configured
- Verify same WiFi network
- Try restarting the dev server

