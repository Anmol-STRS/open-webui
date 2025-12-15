<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { getChatById } from '$lib/apis/chats';
	import ReactPreview from '$lib/components/chat/ReactPreview.svelte';
	import { settings } from '$lib/stores';

	let chatId = $page.params.chatId;
	let artifactIndex = parseInt($page.params.index);
	let code = '';
	let loading = true;
	let error = null;

	// Function to extract code blocks from markdown
	const getCodeBlockContents = (markdown: string) => {
		const codeBlocks: Array<{ lang: string; code: string }> = [];
		const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
		let match;

		while ((match = codeBlockRegex.exec(markdown)) !== null) {
			codeBlocks.push({
				lang: match[1] || '',
				code: match[2].trim()
			});
		}

		return codeBlocks;
	};

	// Get React code blocks from messages
	const getReactCodeFromChat = async () => {
		try {
			const chat = await getChatById(localStorage.token, chatId);

			if (!chat || !chat.chat) {
				error = 'Chat not found';
				loading = false;
				return;
			}

			const messages = Object.values(chat.chat.messages || {});
			let reactBlocks: Array<string> = [];

			messages.forEach((message: any) => {
				if (message?.role === 'assistant' && message?.content) {
					const codeBlocks = getCodeBlockContents(message.content);

					codeBlocks.forEach((block) => {
						const isReact =
							['jsx', 'tsx', 'react'].includes(block.lang?.toLowerCase()) ||
							(['javascript', 'typescript', 'js', 'ts'].includes(block.lang?.toLowerCase()) &&
								/import.*from\s+['"]react['"]|import\s+React|useState|useEffect|<[A-Z]\w*[\s>\/]/.test(
									block.code
								));

						if (isReact) {
							reactBlocks.push(block.code);
						}
					});
				}
			});

			if (reactBlocks.length > artifactIndex) {
				code = reactBlocks[artifactIndex];
			} else {
				error = 'React code not found at this index';
			}

			loading = false;
		} catch (e) {
			error = 'Failed to load chat: ' + e.message;
			loading = false;
		}
	};

	onMount(() => {
		getReactCodeFromChat();
	});
</script>

<svelte:head>
	<title>React Preview - {chatId}</title>
</svelte:head>

<div class="w-screen h-screen bg-gray-50 dark:bg-gray-900">
	{#if loading}
		<div class="flex items-center justify-center h-full">
			<div class="text-gray-600 dark:text-gray-400">Loading preview...</div>
		</div>
	{:else if error}
		<div class="flex items-center justify-center h-full">
			<div class="text-red-600 dark:text-red-400">{error}</div>
		</div>
	{:else}
		<div class="w-full h-full p-4">
			<div class="w-full h-full max-w-7xl mx-auto">
				<ReactPreview
					{code}
					theme={$settings?.theme === 'dark' ? 'dark' : 'light'}
					editable={true}
					showTabs={true}
					showLineNumbers={true}
					showNavigator={false}
				/>
			</div>
		</div>
	{/if}
</div>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		overflow: hidden;
	}
</style>
