<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { 
		Upload, 
		FileText, 
		Trash2, 
		Eye, 
		Download,
		Calendar,
		HardDrive,
		FileIcon,
		Plus
	} from 'lucide-svelte';
	import { 
		pdfList, 
		isLoading, 
		actions, 
		currentPDF 
	} from '$lib/stores';
	import { MarkUIAPI, formatFileSize, formatDate } from '$lib/api';
	import type { PDFDocument } from '$lib/types';

	let fileInput = $state<HTMLInputElement>();
	let dragOver = $state(false);
	let uploading = $state(false);

	onMount(() => {
		actions.loadPDFList();
	});

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
			actions.loadPDFList(); // Refresh the list
			actions.setError(null);
			
			// Show success message
			actions.setError(`Successfully uploaded ${result.original_filename}`);
			setTimeout(() => actions.clearError(), 3000);
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

	async function deletePDF(pdf: PDFDocument) {
		if (!confirm(`Are you sure you want to delete "${pdf.original_filename}"?`)) {
			return;
		}

		try {
			await MarkUIAPI.deletePDF(pdf.id);
			actions.loadPDFList(); // Refresh the list
		} catch (error) {
			actions.setError(`Failed to delete PDF: ${error}`);
		}
	}

	function selectPDFForConversion(pdf: PDFDocument) {
		actions.selectPDF(pdf);
		goto('/convert');
	}
</script>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Header -->
	<div class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
			PDF to Markdown Converter
		</h1>
		<p class="mt-2 text-gray-600 dark:text-gray-400">
			Upload your PDF files and convert them to Markdown, JSON, or HTML with AI enhancement
		</p>
	</div>

	<!-- Upload Area -->
	<div class="mb-8">
		<div
			class="border-2 border-dashed rounded-lg p-8 text-center transition-colors duration-200 {dragOver
				? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
				: 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'}"
			role="button"
			tabindex="0"
			ondrop={handleDrop}
			ondragover={handleDragOver}
			ondragleave={handleDragLeave}
			onkeydown={(e) => {
				if (e.key === 'Enter' || e.key === ' ') {
					e.preventDefault();
					fileInput.click();
				}
			}}
		>
			{#if uploading}
				<div class="flex flex-col items-center">
					<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
					<p class="text-lg font-medium text-gray-900 dark:text-white">Uploading...</p>
				</div>
			{:else}
				<Upload class="mx-auto h-12 w-12 text-gray-400 mb-4" />
				<p class="text-lg font-medium text-gray-900 dark:text-white mb-2">
					Drop your PDF here or click to browse
				</p>
				<p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
					Supports PDF files up to 100MB
				</p>
				<button
					onclick={() => fileInput.click()}
					class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
				>
					<Plus class="w-4 h-4 mr-2" />
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

	<!-- PDF List -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h2 class="text-lg font-medium text-gray-900 dark:text-white">
				Your PDFs ({$pdfList.length})
			</h2>
		</div>

		{#if $isLoading}
			<div class="p-8 text-center">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
				<p class="text-gray-500 dark:text-gray-400">Loading PDFs...</p>
			</div>
		{:else if $pdfList.length === 0}
			<div class="p-8 text-center">
				<FileText class="mx-auto h-12 w-12 text-gray-400 mb-4" />
				<p class="text-lg font-medium text-gray-900 dark:text-white mb-2">No PDFs uploaded yet</p>
				<p class="text-gray-500 dark:text-gray-400">
					Upload your first PDF to get started with conversion
				</p>
			</div>
		{:else}
			<div class="divide-y divide-gray-200 dark:divide-gray-700">
				{#each $pdfList as pdf (pdf.id)}
					<div class="p-6 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-200">
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-4">
								<div class="flex-shrink-0">
									<FileIcon class="h-10 w-10 text-red-500" />
								</div>
								<div class="flex-1 min-w-0">
									<h3 class="text-sm font-medium text-gray-900 dark:text-white truncate">
										{pdf.original_filename}
									</h3>
									<div class="flex items-center space-x-4 mt-1 text-sm text-gray-500 dark:text-gray-400">
										<div class="flex items-center">
											<HardDrive class="w-4 h-4 mr-1" />
											{formatFileSize(pdf.file_size)}
										</div>
										<div class="flex items-center">
											<FileText class="w-4 h-4 mr-1" />
											{pdf.total_pages} pages
										</div>
										<div class="flex items-center">
											<Calendar class="w-4 h-4 mr-1" />
											{formatDate(pdf.created_at)}
										</div>
									</div>
								</div>
							</div>
							
							<div class="flex items-center space-x-2">
								<button
									onclick={() => selectPDFForConversion(pdf)}
									class="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
									title="Convert this PDF"
								>
									<Eye class="w-4 h-4 mr-1" />
									Convert
								</button>
								
								<button
									onclick={() => deletePDF(pdf)}
									class="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors duration-200"
									title="Delete this PDF"
								>
									<Trash2 class="w-4 h-4" />
								</button>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
