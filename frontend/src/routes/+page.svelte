<script lang="ts">
	import { goto } from '$app/navigation';
	import { 
		Upload, 
		Plus
	} from 'lucide-svelte';
	import { 
		isLoading, 
		actions, 
		currentPDF 
	} from '$lib/stores';
	import { MarkUIAPI } from '$lib/api';

	let fileInput = $state<HTMLInputElement>();
	let dragOver = $state(false);
	let uploading = $state(false);

	async function handleFileUpload(files: FileList | null) {
		if (!files || files.length === 0) return;
		
		const file = files[0];
		if (!file.type.includes('pdf')) {
			actions.setError('Please select a PDF file');
			return;
		}

		try {
			uploading = true;
			const result = await MarkUIAPI.uploadPDF(file);
			actions.setError(null);
			
			// Set the uploaded PDF as current and redirect to convert page
			actions.selectPDF({
				id: result.id,
				filename: result.filename,
				original_filename: result.original_filename,
				file_size: result.file_size,
				total_pages: result.total_pages,
				metadata: result.metadata,
				created_at: result.created_at
			});
			
			// Redirect to convert page
			goto('/convert');
		} catch (error) {
			actions.setError(`Upload failed: ${error}`);
		} finally {
			uploading = false;
		}
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		dragOver = false;
		handleFileUpload(event.dataTransfer?.files || null);
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		dragOver = true;
	}

	function handleDragLeave(event: DragEvent) {
		event.preventDefault();
		dragOver = false;
	}
</script>

<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Header -->
	<div class="mb-8 text-center">
		<h1 class="text-4xl font-bold text-gray-900 dark:text-white mb-4">
			PDF to Markdown Converter
		</h1>
		<p class="text-xl text-gray-600 dark:text-gray-400">
			Upload your PDF files and convert them to Markdown, JSON, or HTML with AI enhancement
		</p>
	</div>

	<!-- Upload Area -->
	<div class="max-w-2xl mx-auto">
		<div
			class="border-2 border-dashed rounded-lg p-12 text-center transition-colors duration-200 {dragOver
				? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
				: 'border-gray-200 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'}"
			role="button"
			tabindex="0"
			ondrop={handleDrop}
			ondragover={handleDragOver}
			ondragleave={handleDragLeave}
			onkeydown={(e) => {
				if (e.key === 'Enter' || e.key === ' ') {
					e.preventDefault();
					fileInput?.click();
				}
			}}
		>
			{#if uploading}
				<div class="flex flex-col items-center">
					<div class="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mb-6"></div>
					<p class="text-xl font-medium text-gray-900 dark:text-white">Uploading...</p>
					<p class="text-gray-500 dark:text-gray-400 mt-2">Please wait while we process your PDF</p>
				</div>
			{:else}
				<Upload class="mx-auto h-16 w-16 text-gray-400 mb-6" />
				<p class="text-2xl font-medium text-gray-900 dark:text-white mb-4">
					Drop your PDF here or click to browse
				</p>
				<p class="text-gray-500 dark:text-gray-400 mb-8">
					Supports PDF files up to 100MB
				</p>
				<button
					onclick={() => fileInput?.click()}
					class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200 shadow-lg hover:shadow-xl"
				>
					<Plus class="w-5 h-5 mr-2" />
					Choose File
				</button>
			{/if}
		</div>
		
		<input
			bind:this={fileInput}
			type="file"
			accept=".pdf"
			class="hidden"
			onchange={(e) => handleFileUpload(e.currentTarget.files)}
		/>
	</div>
</div>
