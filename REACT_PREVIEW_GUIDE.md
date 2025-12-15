# React Live Preview Feature

## Overview

The React Live Preview feature allows you to see live, interactive previews of React components generated in the chat. This is powered by **Sandpack** (CodeSandbox's in-browser bundler), providing a full React development environment directly in your browser.

---

## Architecture Integration

### **Component Flow**

```
User asks for React code
         ↓
AI generates React component in chat
         ↓
ContentRenderer detects React code (jsx, tsx, react)
         ↓
Auto-shows Artifacts panel (if detectArtifacts enabled)
         ↓
Chat.svelte's getContents() processes messages
         ↓
Detects React code blocks and adds to artifactContents
         ↓
Artifacts.svelte renders ReactPreview component
         ↓
Sandpack bundles and executes React code
         ↓
Live preview displayed in Artifacts panel
```

### **Key Files Modified**

1. **[ReactPreview.svelte](src/lib/components/chat/ReactPreview.svelte)** (NEW)
   - Wrapper component for Sandpack
   - Handles code parsing and template detection
   - Supports both JavaScript and TypeScript React code

2. **[CodeBlock.svelte](src/lib/components/chat/Messages/CodeBlock.svelte)**
   - Added `checkReactCode()` function to detect React syntax
   - Added "Preview" button for React code blocks
   - Detects: JSX, TSX, React hooks, component patterns

3. **[Artifacts.svelte](src/lib/components/chat/Artifacts.svelte)**
   - Added ReactPreview import
   - Added `type === 'react'` rendering branch
   - Updated download function to support .jsx files
   - Updated empty state message

4. **[Chat.svelte](src/lib/components/chat/Chat.svelte)**
   - Updated `getContents()` to detect React code blocks
   - Adds React code to artifactContents with `type: 'react'`

5. **[ContentRenderer.svelte](src/lib/components/chat/Messages/ContentRenderer.svelte)**
   - Auto-detects React code and shows Artifacts panel
   - Works with existing `detectArtifacts` setting

---

## How It Works

### **1. React Code Detection**

The system detects React code using multiple patterns:

```javascript
// Language indicators
['jsx', 'tsx', 'react'].includes(lang.toLowerCase())

// Code pattern matching
/import.*from\s+['"]react['"]|import\s+React|useState|useEffect|<[A-Z]\w*[\s>\/]/
```

**Detection Patterns:**
- Import statements: `import React from 'react'`
- React hooks: `useState`, `useEffect`, `useContext`, etc.
- JSX syntax: `<ComponentName>`
- React.Component class usage
- JSX attributes: `className=`

### **2. Code Parsing and Wrapping**

ReactPreview intelligently wraps your code based on its structure:

**Case 1: Full App (has ReactDOM.render or createRoot)**
```javascript
// Your code is used as-is
import React from 'react';
import ReactDOM from 'react-dom/client';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
```

**Case 2: Component with export default**
```javascript
// Your component
export default function MyComponent() {
  return <div>Hello</div>;
}

// Auto-wrapped with index.js:
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
```

**Case 3: Bare component code**
```javascript
// Your component
function App() {
  const [count, setCount] = useState(0);
  return <div>{count}</div>;
}

// Auto-wrapped with imports and export
import React from 'react';
function App() { /* your code */ }
export default App;
```

### **3. TypeScript Support**

The system automatically detects TypeScript by looking for:
- Type annotations: `: string`, `: number`, etc.
- Interfaces: `interface Props`
- Type aliases: `type MyType =`
- React.FC usage with generics

When detected, it uses the `react-ts` template instead of `react`.

---

## Usage Examples

### **Example 1: Simple Counter Component**

Ask the AI:
```
Create a React counter component with increment and decrement buttons
```

The AI might generate:
````markdown
```jsx
import React, { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);

  return (
    <div style={{ padding: '20px', textAlign: 'center' }}>
      <h1>Count: {count}</h1>
      <button onClick={() => setCount(count - 1)}>-</button>
      <button onClick={() => setCount(count + 1)}>+</button>
    </div>
  );
}

export default Counter;
```
````

**What happens:**
1. Code block appears in chat with syntax highlighting
2. "Preview" button appears in code block header
3. Artifacts panel auto-opens (if detectArtifacts is enabled)
4. Live preview shows interactive counter
5. You can click buttons and see state updates in real-time

### **Example 2: TypeScript Component with Props**

Ask the AI:
```
Create a TypeScript React card component that accepts title and content props
```

````typescript
```tsx
import React from 'react';

interface CardProps {
  title: string;
  content: string;
}

const Card: React.FC<CardProps> = ({ title, content }) => {
  return (
    <div style={{
      border: '1px solid #ddd',
      borderRadius: '8px',
      padding: '16px',
      margin: '8px'
    }}>
      <h2>{title}</h2>
      <p>{content}</p>
    </div>
  );
}

export default Card;
```
````

**Result:** TypeScript-enabled Sandpack environment with full type checking

### **Example 3: Component with Hooks**

````jsx
```jsx
import React, { useState, useEffect } from 'react';

function Timer() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setSeconds(s => s + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ fontSize: '48px', textAlign: 'center', padding: '40px' }}>
      {seconds}s
    </div>
  );
}

export default Timer;
```
````

**Result:** Live timer that updates every second in the preview

---

## Features

### **Sandpack Capabilities**

✅ **Full React Environment**
- React 18+ with hooks
- Modern JavaScript/TypeScript
- Hot module reloading
- Error boundaries

✅ **NPM Package Support**
- Can import common packages (React, ReactDOM)
- No need to install dependencies manually

✅ **Live Updates**
- Changes reflect immediately (500ms debounce)
- No manual refresh needed

✅ **Error Handling**
- Shows compilation errors
- Runtime error boundaries
- Clear error messages

### **UI Features**

- **Version Navigation**: Navigate between different React code versions
- **Copy**: Copy React code to clipboard
- **Download**: Download as .jsx or .tsx file
- **Theme Support**: Follows Open WebUI dark/light theme
- **Fullscreen**: Not available for React (Sandpack limitation), but preview is resizable

---

## Configuration

### **User Settings**

The feature respects existing Open WebUI settings:

**`detectArtifacts`** (default: `true`)
- When enabled, React code automatically opens the Artifacts panel
- When disabled, user must click "Preview" button manually

**`theme`** (inherited from Open WebUI)
- Dark theme: Uses Sandpack dark theme
- Light theme: Uses Sandpack light theme

### **ReactPreview Component Props**

```typescript
interface ReactPreviewProps {
  code: string;              // React code to preview
  theme?: 'light' | 'dark';  // Color theme
  editable?: boolean;        // Show code editor (default: false)
  showTabs?: boolean;        // Show file tabs (default: false)
  showLineNumbers?: boolean; // Show line numbers (default: false)
  showNavigator?: boolean;   // Show file navigator (default: false)
}
```

**Current Defaults in Artifacts:**
- `editable: false` - Preview only, no inline editing
- `showTabs: false` - Cleaner UI
- `showLineNumbers: false` - Simpler preview
- `showNavigator: false` - Hide file tree

**To enable code editing**, modify [Artifacts.svelte](src/lib/components/chat/Artifacts.svelte:257-264):
```svelte
<ReactPreview
  code={contents[selectedContentIdx].content}
  theme={$settings?.theme === 'dark' ? 'dark' : 'light'}
  editable={true}  <!-- Change to true -->
  showTabs={true}
  showLineNumbers={true}
/>
```

---

## Limitations

### **Current Limitations**

1. **No External Package Installation**
   - Can only use packages included in Sandpack by default
   - Custom npm packages require template modification

2. **No Fullscreen for React**
   - HTML iframes support fullscreen
   - Sandpack doesn't support fullscreen API well

3. **Browser Performance**
   - Complex components may be slower
   - Bundling happens in-browser

4. **No Server-Side Features**
   - No API calls to real backends
   - No database connections
   - Client-side only

### **Workarounds**

**For External Packages:**
You can modify the Sandpack template to include more packages:
```javascript
// In ReactPreview.svelte, add dependencies
options={{
  dependencies: {
    'lodash': 'latest',
    'date-fns': 'latest'
  }
}}
```

**For API Calls:**
Use mock data or public APIs:
```jsx
// Works fine
fetch('https://jsonplaceholder.typicode.com/todos/1')
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## Troubleshooting

### **Problem: Preview button doesn't appear**

**Causes:**
1. Code not detected as React
2. `preview` prop not set to `true`

**Solutions:**
- Use explicit language tag: ` ```jsx ` or ` ```tsx `
- Include React imports in code
- Check that code includes React patterns (hooks, JSX, etc.)

### **Problem: Artifacts panel doesn't auto-open**

**Causes:**
1. `detectArtifacts` setting is disabled
2. On mobile device
3. Not in a chat (chatId is null)

**Solutions:**
- Enable detectArtifacts in settings
- Click "Preview" button manually
- Ensure you're in an active chat

### **Problem: Code shows errors in preview**

**Common Errors:**

**1. "React is not defined"**
```jsx
// Missing import
function App() { return <div>Hi</div>; }

// Fixed
import React from 'react';
function App() { return <div>Hi</div>; }
```

**2. "useState is not a function"**
```jsx
// Missing hook import
import React from 'react';
function App() {
  const [count, setCount] = useState(0);  // ❌
}

// Fixed
import React, { useState } from 'react';
function App() {
  const [count, setCount] = useState(0);  // ✅
}
```

**3. TypeScript errors with JavaScript code**
```jsx
// Code is treated as TypeScript
interface Props { }  // ❌ in JS file

// Solution: Use .jsx tag
```

### **Problem: Preview is blank**

**Causes:**
1. Component doesn't render anything
2. Runtime error in code
3. Missing export default

**Solutions:**
- Check browser console for errors
- Ensure component returns JSX
- Add `export default YourComponent`

---

## Developer Notes

### **Adding Custom Sandpack Templates**

Edit [ReactPreview.svelte](src/lib/components/chat/ReactPreview.svelte) to add custom templates:

```javascript
const customTemplate = {
  files: {
    '/App.js': {
      code: `import './styles.css';\n${code}`
    },
    '/styles.css': {
      code: `body { font-family: system-ui; }`
    }
  },
  dependencies: {
    'react-router-dom': 'latest'
  }
};
```

### **Customizing Sandpack Theme**

```javascript
import { githubLight } from '@codesandbox/sandpack-themes';

<Sandpack
  theme={theme === 'dark' ? 'dark' : githubLight}
  // ... other props
/>
```

### **Performance Optimization**

For large codebases, consider:
1. Debouncing code updates (already implemented: 500ms)
2. Lazy loading ReactPreview component
3. Virtualizing artifact list if many previews

---

## Future Enhancements

### **Possible Improvements**

1. **Editable Preview Mode**
   - Allow users to edit code directly in Sandpack
   - Sync changes back to chat message

2. **Package Installation UI**
   - UI to add npm packages dynamically
   - Auto-detect package imports

3. **Template Library**
   - Pre-built templates (React + Tailwind, React + Material-UI, etc.)
   - User-selectable from UI

4. **Export Options**
   - Export to CodeSandbox
   - Export to StackBlitz
   - Download as full project zip

5. **Multi-File Support**
   - Parse multiple file code blocks
   - Create file structure in Sandpack

6. **Console Output**
   - Show console.log output
   - Display errors in UI

7. **React Native Preview**
   - Use Expo Snack for React Native code
   - Mobile component preview

---

## Code Examples for Testing

### **Test 1: Basic Component**
```
Create a simple React greeting component that displays "Hello, World!"
```

### **Test 2: Stateful Component**
```
Create a React todo list with add and delete functionality
```

### **Test 3: TypeScript Component**
```
Create a TypeScript React button component with variant props (primary, secondary, danger)
```

### **Test 4: Hooks Example**
```
Create a React component that fetches and displays data from https://jsonplaceholder.typicode.com/users
```

### **Test 5: Styled Component**
```
Create a React card component with hover effects using inline styles
```

---

## Summary

The React Live Preview feature integrates seamlessly with Open WebUI's existing artifact system, providing:

✅ Automatic React code detection
✅ Live, interactive previews powered by Sandpack
✅ Support for both JavaScript and TypeScript
✅ Dark/light theme support
✅ Version navigation
✅ Download as .jsx/.tsx files
✅ Zero configuration for users

The implementation follows Open WebUI's architecture patterns and extends the existing code preview system to support modern React development workflows.
