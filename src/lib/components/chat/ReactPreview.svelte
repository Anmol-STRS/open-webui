<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	export let code: string = '';
	export let theme: 'light' | 'dark' = 'dark';
	export let editable: boolean = false;
	export let showTabs: boolean = true;
	export let showLineNumbers: boolean = true;
	export let showNavigator: boolean = false;

	let container: HTMLDivElement;
	let sandpackInstance: any;
	let React: any;
	let ReactDOM: any;
	let Sandpack: any;

	// Parse code to detect if it's a full app or just a component
	const parseReactCode = (code: string) => {
		const hasImport = /import\s+.*from/.test(code);
		const hasExportDefault = /export\s+default/.test(code);
		const hasReactDOMRender = /ReactDOM\.render|createRoot/.test(code);

		// If it has ReactDOM.render or createRoot, it's a full app
		if (hasReactDOMRender) {
			return {
				'/App.js': code
			};
		}

		// If it has export default, wrap it in an index.js
		if (hasExportDefault) {
			return {
				'/App.js': code,
				'/index.js': `import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);`
			};
		}

		// Otherwise, treat it as a component to be rendered
		return {
			'/App.js': `import React from 'react';

${code}

export default App;`,
			'/index.js': `import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);`
		};
	};

	// Detect if code uses TypeScript
	const isTypeScript = (code: string) => {
		return (
			/:\s*(string|number|boolean|any|void|Array|Object)\b/.test(code) ||
			/interface\s+\w+/.test(code) ||
			/type\s+\w+\s*=/.test(code) ||
			/<.*>/.test(code) && /React\.FC/.test(code)
		);
	};

	$: files = parseReactCode(code);
	$: template = isTypeScript(code) ? 'react-ts' : 'react';

	let root: any = null;

	const renderSandpack = () => {
		if (container && React && ReactDOM && Sandpack) {
			// Cleanup previous render
			if (root) {
				try {
					root.unmount();
				} catch (e) {
					// Ignore
				}
			}

			// Create new root and render
			root = ReactDOM.createRoot(container);
			root.render(
				React.createElement(Sandpack, {
					template,
					files,
					theme: theme === 'dark' ? 'dark' : 'light',
					options: {
						showNavigator,
						showTabs,
						showLineNumbers,
						editorHeight: '100%',
						editorWidthPercentage: editable ? 50 : 0,
						classes: {
							'sp-wrapper': 'sandpack-custom-wrapper',
							'sp-layout': 'sandpack-custom-layout'
						},
						autorun: true,
						autoReload: true,
						recompileMode: 'delayed',
						recompileDelay: 500
					}
				})
			);
		}
	};

	onMount(async () => {
		// Dynamically import React and Sandpack
		React = (await import('react')).default;
		ReactDOM = (await import('react-dom/client')).default;
		const sandpackModule = await import('@codesandbox/sandpack-react');
		Sandpack = sandpackModule.Sandpack;

		renderSandpack();
	});

	// Re-render when code or theme changes
	$: if (code || theme) {
		renderSandpack();
	}

	onDestroy(() => {
		// Cleanup React root
		if (root) {
			try {
				root.unmount();
			} catch (e) {
				// Ignore unmount errors
			}
		}
	});
</script>

<div bind:this={container} class="w-full h-full sandpack-wrapper"></div>

<style>
	.sandpack-wrapper {
		border-radius: 0.75rem;
		overflow: hidden;
		min-height: 400px;
		height: 100%;
		display: flex;
		flex-direction: column;
	}

	:global(.sandpack-custom-wrapper) {
		border-radius: 0.75rem;
		height: 100% !important;
		display: flex !important;
		flex-direction: column !important;
	}

	:global(.sandpack-custom-layout) {
		border: none !important;
		border-radius: 0.75rem;
		height: 100% !important;
		flex: 1 !important;
		display: flex !important;
		flex-direction: row !important;
	}

	:global(.sp-preview-container) {
		background: white;
		height: 100% !important;
		flex: 1 !important;
	}

	:global([data-theme='dark'] .sp-preview-container) {
		background: #1a1a1a;
	}

	:global(.sp-preview-iframe) {
		height: 100% !important;
	}

	:global(.sp-stack) {
		height: 100% !important;
	}
</style>
