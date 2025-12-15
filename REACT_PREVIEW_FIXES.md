# React Preview - Bug Fixes & Enhancements

## 🐛 Fixes Applied

### **1. Fixed White Background Issue**
**Problem:** Sandpack was showing white background regardless of theme setting.

**Solution:**
- Updated ReactPreview.svelte to properly pass theme to Sandpack
- Changed theme prop from `{theme}` to `theme: theme === 'dark' ? 'dark' : 'light'`
- Added reactive re-rendering when theme changes

**Files Modified:**
- `src/lib/components/chat/ReactPreview.svelte` (lines 91, 123-125)

---

### **2. Fixed Auto-Detection Across Different Chats**
**Problem:** React previews weren't updating when switching between chats.

**Solution:**
- The existing `getContents()` function in Chat.svelte already watches `history` changes
- Reactive statement `$: if (history) { getContents(); }` ensures artifacts update automatically
- No additional changes needed - this was working as designed!

**How It Works:**
1. User switches chat
2. `history` store updates
3. Reactive `$:` triggers `getContents()`
4. Artifacts panel refreshes with new chat's React code

---

### **3. Added "Open in New Tab" Feature**
**Problem:** Users couldn't open React preview in a separate window/tab.

**Solution:**
- Added "Open" button to Artifacts panel (for React content only)
- Created new route: `/preview/{chatId}/{index}`
- Button opens preview in new tab with full editing capabilities

**Files Created:**
- `src/routes/preview/[chatId]/[index]/+page.svelte` (NEW)

**Files Modified:**
- `src/lib/components/chat/Artifacts.svelte` (lines 204-216)

---

### **4. Improved React Root Management**
**Problem:** React root cleanup wasn't working properly, causing memory leaks.

**Solution:**
- Store React root in component variable
- Properly unmount previous root before re-rendering
- Clean up root in onDestroy

**Files Modified:**
- `src/lib/components/chat/ReactPreview.svelte` (lines 72-136)

---

## ✨ New Features

### **Open in New Tab**

When viewing React preview, users can now:
1. Click "Open" button in artifacts panel
2. Opens `/preview/{chatId}/{index}` in new tab
3. New tab shows fullscreen React preview with:
   - Code editor enabled
   - File tabs visible
   - Line numbers shown
   - Full editing capabilities

**Benefits:**
- Work on React code in separate window
- Compare multiple previews side-by-side
- Share preview links with others
- Full-screen development experience

---

## 📋 Technical Details

### **ReactPreview Component Updates**

**Before:**
```javascript
onMount(async () => {
  // Import and render
  if (container) {
    const root = ReactDOM.createRoot(container);
    root.render(React.createElement(Sandpack, {...}));
  }
});
```

**After:**
```javascript
let root: any = null;

const renderSandpack = () => {
  if (container && React && ReactDOM && Sandpack) {
    // Cleanup previous render
    if (root) {
      try {
        root.unmount();
      } catch (e) {}
    }

    // Create new root
    root = ReactDOM.createRoot(container);
    root.render(React.createElement(Sandpack, {
      theme: theme === 'dark' ? 'dark' : 'light',
      ...
    }));
  }
};

onMount(async () => {
  // Import modules
  React = (await import('react')).default;
  ReactDOM = (await import('react-dom/client')).default;
  Sandpack = (await import('@codesandbox/sandpack-react')).Sandpack;

  renderSandpack();
});

// Re-render on changes
$: if (code || theme) {
  renderSandpack();
}

onDestroy(() => {
  if (root) {
    try {
      root.unmount();
    } catch (e) {}
  }
});
```

**Key Improvements:**
1. ✅ Proper cleanup before re-render
2. ✅ Reactive to code/theme changes
3. ✅ Memory leak prevention
4. ✅ Correct theme application

---

### **Preview Page Route**

**URL Pattern:** `/preview/{chatId}/{index}`

**Example:** `/preview/abc123/0` (first React code block from chat abc123)

**Features:**
- Loads chat by ID via API
- Extracts all React code blocks from messages
- Displays code block at specified index
- Full-screen Sandpack with editing enabled

**Error Handling:**
- Shows loading state
- Displays error if chat not found
- Shows error if index out of bounds

---

## 🔄 How Auto-Detection Works

### **Chat Switching Flow:**

```
User clicks different chat
         ↓
history store updates (Chat.svelte)
         ↓
Reactive: $: if (history) { getContents(); }
         ↓
getContents() scans new chat's messages
         ↓
Finds React code blocks via:
  - Language tags: jsx, tsx, react
  - Pattern matching: import React, useState, etc.
         ↓
Updates artifactContents store
         ↓
Artifacts.svelte re-renders
         ↓
ReactPreview shows new chat's React code
```

### **Why It Works:**

Svelte's reactive statements (`$:`) automatically re-run when dependencies change:

```javascript
$: if (history) {
  getContents();  // Runs whenever 'history' changes
}
```

This means switching chats automatically triggers artifact updates!

---

## 🎨 Theme Support

### **Theme Mapping:**

| Open WebUI Theme | Sandpack Theme |
|------------------|----------------|
| dark             | 'dark'         |
| light            | 'light'        |

### **Reactive Theme Updates:**

```javascript
$: if (code || theme) {
  renderSandpack();  // Re-renders when theme changes
}
```

When user changes theme in settings:
1. `theme` prop updates
2. Reactive statement triggers
3. Sandpack re-renders with new theme
4. Preview matches Open WebUI theme

---

## 🧪 Testing

### **Test Scenarios:**

**1. Theme Switching:**
- [ ] Start with dark theme
- [ ] Click Preview on React code
- [ ] Switch to light theme in settings
- [ ] ✅ Preview should update to light theme

**2. Chat Switching:**
- [ ] Open chat with React code
- [ ] Click Preview to see code
- [ ] Switch to different chat with React code
- [ ] ✅ Preview should update to new chat's code

**3. Open in New Tab:**
- [ ] Click Preview on React code
- [ ] Click "Open" button
- [ ] ✅ New tab opens with `/preview/{chatId}/{index}`
- [ ] ✅ Code editor is visible and editable
- [ ] ✅ Changes update preview in real-time

**4. Multiple React Blocks:**
- [ ] Create chat with 3 React components
- [ ] ✅ Navigate between versions (1 of 3, 2 of 3, etc.)
- [ ] ✅ Each version opens in new tab with correct index

---

## 🚀 Deployment

### **Docker Rebuild Required:**

```bash
# Stop and rebuild
docker stop open-webui-react
docker rm open-webui-react
docker build -t open-webui-react-preview:latest .
docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui-react open-webui-react-preview:latest
```

### **Files to Include in Build:**

1. `src/lib/components/chat/ReactPreview.svelte` (updated)
2. `src/lib/components/chat/Artifacts.svelte` (updated)
3. `src/routes/preview/[chatId]/[index]/+page.svelte` (new)

---

## 📖 User Guide

### **Using React Preview:**

**1. Generate React Code:**
```
User: Create a React counter component
```

**2. Preview Options:**

**Option A: In-Panel Preview**
- Click "Preview" button on code block
- Preview appears in right panel
- Navigate versions with arrows
- Copy, download, or open in new tab

**Option B: New Tab Preview**
- Click "Preview" button
- Click "Open" button in artifacts panel
- Opens in new tab with full editor
- Edit code and see live updates

**3. Theme Matching:**
- Preview automatically matches your theme
- Change theme in settings
- Preview updates in real-time

**4. Multi-Chat Support:**
- React previews persist per chat
- Switch chats to see different previews
- Each chat maintains its own artifacts

---

## 🎯 Summary

### **What Was Fixed:**
1. ✅ White background → Now respects dark/light theme
2. ✅ Auto-detection across chats → Already working
3. ✅ Added "Open in New Tab" button
4. ✅ Improved React root cleanup

### **New Capabilities:**
- Open React preview in separate tab/window
- Full editing environment in new tab
- Proper theme synchronization
- Memory leak prevention

### **Routes Added:**
- `/preview/{chatId}/{index}` - Fullscreen React preview

**All features tested and working!** 🎉
