# Open WebUI Architecture Overview

## Complete System Architecture

This document provides a comprehensive overview of Open WebUI's architecture, with special focus on the newly integrated React Live Preview feature.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        OPEN WEBUI                                │
│                                                                   │
│  ┌─────────────────┐         ┌──────────────────┐              │
│  │   Frontend      │◄────────┤   Backend        │              │
│  │   SvelteKit     │   API   │   FastAPI        │              │
│  │                 │─────────►│   Python         │              │
│  └────────┬────────┘         └─────────┬────────┘              │
│           │                             │                        │
│           │                             │                        │
│  ┌────────▼────────┐         ┌─────────▼────────┐              │
│  │  Chat UI        │         │  LLM Integration │              │
│  │  Components     │         │  (OpenAI, etc.)  │              │
│  └────────┬────────┘         └──────────────────┘              │
│           │                                                      │
│  ┌────────▼──────────────────────────────────┐                 │
│  │        Message Rendering Pipeline         │                 │
│  │  Markdown → Tokens → Components           │                 │
│  └────────┬──────────────────────────────────┘                 │
│           │                                                      │
│  ┌────────▼────────┬─────────────┬──────────────┐              │
│  │  CodeBlock      │  Artifacts  │  ReactPreview│              │
│  │  (Syntax)       │  (Preview)  │  (Sandpack)  │ ◄── NEW!    │
│  └─────────────────┴─────────────┴──────────────┘              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture (Svelte/SvelteKit)

### **Directory Structure**

```
src/
├── routes/                      # SvelteKit routes
│   ├── +page.svelte            # Home page
│   └── +layout.svelte          # Global layout
│
├── lib/
│   ├── components/
│   │   ├── chat/
│   │   │   ├── Chat.svelte                 # Main chat container
│   │   │   ├── Artifacts.svelte            # Preview panel (HTML/SVG/React)
│   │   │   ├── ReactPreview.svelte         # ✨ NEW: React preview
│   │   │   ├── Messages/
│   │   │   │   ├── Messages.svelte         # Message list
│   │   │   │   ├── Message.svelte          # Message wrapper
│   │   │   │   ├── UserMessage.svelte      # User messages
│   │   │   │   ├── ResponseMessage.svelte  # AI responses
│   │   │   │   ├── ContentRenderer.svelte  # Content parser
│   │   │   │   └── Markdown/
│   │   │   │       ├── Markdown.svelte     # Markdown entry point
│   │   │   │       ├── MarkdownTokens.svelte   # Token renderer
│   │   │   │       └── CodeBlock.svelte        # Code blocks + execution
│   │   │   │
│   │   │   └── ChatControls/
│   │   │       └── ...
│   │   │
│   │   ├── common/             # Shared components
│   │   │   ├── CodeEditor.svelte
│   │   │   ├── SvgPanZoom.svelte
│   │   │   └── ...
│   │   │
│   │   └── admin/              # Admin panels
│   │       └── Settings/
│   │
│   ├── stores/                 # Svelte stores (state management)
│   │   └── index.ts            # Global stores
│   │
│   ├── utils/                  # Utility functions
│   │   ├── index.ts            # General utilities
│   │   └── marked/             # Markdown extensions
│   │
│   ├── workers/                # Web Workers
│   │   └── pyodide.worker.ts   # Python execution
│   │
│   └── apis/                   # API clients
│       └── utils.ts
│
└── static/                     # Static assets
```

---

## Chat Message Flow - Detailed

### **1. User Sends Message**

```
User Input
    ↓
Chat.svelte (handleSubmit)
    ↓
API Call to Backend
    ↓
Backend → LLM (OpenAI/Ollama/etc.)
    ↓
Streaming Response ← Backend
    ↓
Messages Store Updated
    ↓
Messages.svelte Re-renders
```

### **2. Message Rendering Pipeline**

```
Message Object
    ↓
Message.svelte
    ↓
┌───────────┴───────────┐
│                       │
UserMessage.svelte   ResponseMessage.svelte
                          ↓
                   ContentRenderer.svelte
                          ↓
                   Markdown.svelte
                          ↓
                   marked.lexer() → Tokens[]
                          ↓
                   MarkdownTokens.svelte
                          ↓
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
    Code Token      Text Token      Table Token
          ↓               ↓               ↓
    CodeBlock      TextToken       TableRenderer
```

### **3. Code Block Rendering**

```
CodeBlock.svelte
    ↓
┌───────────┴──────────┐
│                      │
Language Detection     Syntax Highlighting
│                      │
├─ Python?             highlight.js
├─ React/JSX? ✨       │
├─ HTML/SVG?           ↓
└─ Mermaid?         Rendered Code
    │
    ↓
Action Buttons:
├─ Copy
├─ Collapse/Expand
├─ Run (Python) ─────► Pyodide/Jupyter
└─ Preview (HTML/React) ─► Artifacts Panel
```

---

## Artifacts System Architecture

### **Data Flow**

```
CodeBlock Preview Click
         ↓
   onPreview callback
         ↓
   ContentRenderer
         ↓
   Updates Stores:
   ├─ artifactCode
   ├─ artifactContents
   ├─ showArtifacts ← true
   └─ showControls ← true
         ↓
   Artifacts.svelte subscribes
         ↓
   Renders based on type:
   ├─ iframe → HTML Preview
   ├─ svg → SVG Pan/Zoom
   └─ react → ReactPreview ✨
```

### **Artifact Content Processing**

```
Chat.svelte - getContents()
         ↓
   Scans all messages
         ↓
   Extracts code blocks
         ↓
   ┌──────┴──────────────────┐
   │                         │
   HTML/CSS/JS?          SVG?
   │                         │
   Combine into           Extract SVG
   HTML template              │
   │                         │
   {type:'iframe',        {type:'svg',
    content:html}          content:svg}
   │                         │
   └──────┬──────────────────┘
         │
      React? ✨
         │
   {type:'react',
    content:jsxCode}
         ↓
   artifactContents.set([...])
```

---

## React Preview System ✨

### **Component Hierarchy**

```
Artifacts.svelte
    ↓
ReactPreview.svelte
    ↓
┌───────────┴──────────┐
│                      │
Code Parser      Sandpack Component
│                      │
├─ Detect Type         ├─ File System
│  ├─ Full App         │  ├─ /App.js
│  ├─ Component        │  └─ /index.js
│  └─ TypeScript       │
│                      ├─ Bundler
├─ Wrap Code           │  └─ esbuild (WASM)
│  ├─ Add imports      │
│  ├─ Add exports      ├─ Runtime
│  └─ Create index     │  └─ React 18
│                      │
└─────────┬────────────┘
          │
    Live Preview
    (Interactive)
```

### **React Code Detection Logic**

```javascript
// Step 1: Language Tag Check
if (['jsx', 'tsx', 'react'].includes(lang.toLowerCase())) {
  return true;
}

// Step 2: Content Pattern Check
const reactPatterns = [
  /import.*from\s+['"]react['"]/,  // Import statements
  /import\s+React/,                 // React import
  /<[A-Z]\w*[\s>\/]/,              // JSX component tags
  /useState|useEffect|useContext/,  // React hooks
  /React\.Component/,               // Class components
  /className=/,                     // JSX className
  /export\s+default\s+function/    // Component export
];

return reactPatterns.some(pattern => pattern.test(code));
```

### **Code Transformation**

```javascript
// Input: Bare component
function Counter() {
  const [count, setCount] = useState(0);
  return <div>{count}</div>;
}

// ↓ ReactPreview transforms to ↓

// /App.js
import React, { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);
  return <div>{count}</div>;
}

export default Counter;

// /index.js
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
```

---

## Store Architecture

### **Global Stores** (src/lib/stores/index.ts)

```typescript
// Chat State
export const chatId = writable<string | null>(null);
export const messages = writable<Message[]>([]);
export const currentMessageId = writable<string | null>(null);

// Artifact State ✨
export const artifactCode = writable<string>('');
export const artifactContents = writable<ArtifactContent[]>([]);
export const showArtifacts = writable<boolean>(false);
export const showControls = writable<boolean>(false);

// User Settings
export const settings = writable<Settings>({
  detectArtifacts: true,  // Auto-show artifacts
  theme: 'dark',
  // ... more settings
});

// Configuration
export const config = writable<Config>({
  features: {
    enable_code_execution: true
  },
  code: {
    engine: 'pyodide' // or 'jupyter'
  }
});
```

### **Store Flow Example**

```
User clicks "Preview" on React code
         ↓
CodeBlock.svelte: onPreview(code)
         ↓
ContentRenderer: onPreview callback
         ↓
artifactCode.set(code)
showArtifacts.set(true)
showControls.set(true)
         ↓
Artifacts.svelte subscribes to stores
         ↓
$artifactCode changes → triggers reactivity
         ↓
Artifacts re-renders with ReactPreview
```

---

## Backend Architecture (Python/FastAPI)

### **Directory Structure**

```
backend/
├── open_webui/
│   ├── routers/
│   │   ├── utils.py              # Code execution endpoint
│   │   ├── chats.py              # Chat CRUD
│   │   ├── models.py             # Model management
│   │   └── ...
│   │
│   ├── services/
│   │   └── code_interpreter.py   # Jupyter integration
│   │
│   ├── models/
│   │   └── ...                   # Database models
│   │
│   └── static/
│       └── ...                   # Static files
│
└── requirements.txt
```

### **Code Execution Flow**

```
Frontend: CodeBlock "Run" button
         ↓
   Check engine type
         ↓
┌────────┴────────┐
│                 │
Pyodide       Jupyter
(Browser)     (Server)
│                 │
Web Worker        ↓
│            POST /api/utils/code/execute
│                 ↓
│            utils.py router
│                 ↓
│            code_interpreter.py
│                 ↓
│            Jupyter Kernel
│                 ↓
│            Execute Python
│                 ↓
│            Return {stdout, stderr, result}
│                 │
└────────┬────────┘
         ↓
   CodeBlock displays results
```

---

## Integration Points

### **1. Markdown Extensions**

Located in `src/lib/utils/marked/`

```
marked.js (core library)
    ↓
Custom Extensions:
├── citation-extension.ts       # [@source]
├── footnote-extension.ts       # [^1]
├── katex-extension.ts          # Math equations
├── mention-extension.ts        # @mentions
└── strikethrough-extension.ts  # ~~text~~
    ↓
MarkdownTokens.svelte processes extended tokens
```

### **2. Code Execution Engines**

```
┌─────────────────────────────────────┐
│      Code Execution System          │
├─────────────────────────────────────┤
│                                     │
│  Pyodide (Client-side)              │
│  ├── Runs in Web Worker             │
│  ├── Python in WebAssembly          │
│  ├── Auto package install           │
│  └── Matplotlib → base64 images     │
│                                     │
│  Jupyter (Server-side)              │
│  ├── External Jupyter server        │
│  ├── Token/password auth            │
│  ├── Full Python environment        │
│  └── Custom package support         │
│                                     │
└─────────────────────────────────────┘
```

### **3. Artifact Types**

```
┌─────────────────────────────────────┐
│         Artifact System             │
├─────────────────────────────────────┤
│                                     │
│  iframe (HTML/CSS/JS)               │
│  ├── Sandboxed iframe               │
│  ├── Combined HTML template         │
│  └── allow-scripts, allow-downloads │
│                                     │
│  svg (SVG/XML)                      │
│  ├── SvgPanZoom component           │
│  ├── Pan and zoom controls          │
│  └── Vector graphics                │
│                                     │
│  react (JSX/TSX) ✨                │
│  ├── ReactPreview component         │
│  ├── Sandpack bundler               │
│  ├── Live state management          │
│  └── Interactive preview            │
│                                     │
└─────────────────────────────────────┘
```

---

## Technology Stack

### **Frontend**

- **Framework:** SvelteKit 2.x
- **Language:** TypeScript
- **UI Library:** Tailwind CSS 4.x
- **Rich Text:** TipTap
- **Code Editor:** CodeMirror 6
- **Markdown:** marked.js
- **Math Rendering:** KaTeX
- **Diagrams:** Mermaid
- **Data Viz:** Vega/Vega-Lite
- **React Preview:** Sandpack ✨

### **Backend**

- **Framework:** FastAPI
- **Language:** Python 3.10+
- **Database:** SQLite/PostgreSQL
- **ORM:** SQLAlchemy
- **LLM Integration:** OpenAI SDK, Anthropic, etc.

### **Build Tools**

- **Bundler:** Vite 5.x
- **Package Manager:** npm
- **Linter:** ESLint
- **Formatter:** Prettier
- **Type Checking:** TypeScript

---

## Key Design Patterns

### **1. Reactive Store Pattern**

```svelte
<!-- Component subscribes to store -->
<script>
  import { artifactContents } from '$lib/stores';

  // Auto-subscribes with $
  $: console.log($artifactContents);
</script>

<!-- Reactive updates -->
{#each $artifactContents as artifact}
  <div>{artifact.content}</div>
{/each}
```

### **2. Event Delegation Pattern**

```svelte
<!-- Parent component -->
<CodeBlock
  onPreview={(code) => {
    artifactCode.set(code);
    showArtifacts.set(true);
  }}
/>
```

### **3. Component Composition**

```
Chat.svelte
  └── Messages.svelte
      └── Message.svelte
          ├── UserMessage.svelte
          └── ResponseMessage.svelte
              └── ContentRenderer.svelte
                  └── Markdown.svelte
                      └── MarkdownTokens.svelte
                          ├── CodeBlock.svelte
                          ├── TextToken.svelte
                          └── ...
```

---

## Performance Considerations

### **Code Splitting**

- Routes are automatically code-split by SvelteKit
- Heavy components (Sandpack) lazy loaded
- Web Workers for CPU-intensive tasks

### **Caching**

- Artifact contents cached in store
- Pyodide packages cached in browser
- Message history optimized with virtual scrolling

### **Bundling**

- Vite optimizes bundle size
- Tree-shaking removes unused code
- Dynamic imports for large libraries

---

## Security Model

### **Iframe Sandboxing**

```html
<iframe
  sandbox="allow-scripts allow-downloads"
  srcdoc={htmlContent}
/>
```

Prevents:
- Form submission
- Same-origin access
- Popups
- Navigation

### **Code Execution**

**Pyodide (Browser):**
- Runs in Web Worker (isolated thread)
- No file system access
- No network by default
- Timeout protection (60s)

**Jupyter (Server):**
- Requires authentication
- Admin-configurable
- Runs in separate process
- Timeout protection

### **React Preview (Sandpack)**

- Runs in sandboxed iframe
- No access to parent window
- No localStorage/cookies access
- CORS protected

---

## Summary

Open WebUI's architecture is:

✅ **Modular:** Clear separation of concerns
✅ **Reactive:** Real-time updates with Svelte stores
✅ **Extensible:** Easy to add new features (like React preview)
✅ **Performant:** Lazy loading, code splitting, caching
✅ **Secure:** Sandboxing, authentication, timeouts
✅ **Type-Safe:** TypeScript throughout
✅ **Well-Structured:** Logical component hierarchy

The React Live Preview feature integrates seamlessly by:
- Following existing patterns (Artifacts system)
- Using established stores (artifactContents)
- Extending detection logic (checkReactCode)
- Adding new component type ('react')
- Leveraging existing infrastructure (CodeBlock, ContentRenderer)
