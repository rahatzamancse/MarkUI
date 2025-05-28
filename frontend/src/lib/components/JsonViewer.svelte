<script lang="ts">
	import { ChevronRight, ChevronDown, Copy, Check } from 'lucide-svelte';
	import JsonViewer from './JsonViewer.svelte';

	interface Props {
		data: any;
		expanded?: boolean;
		level?: number;
		parentKey?: string;
	}

	let { data, expanded = true, level = 0, parentKey }: Props = $props();

	let isExpanded = $state(expanded);
	let copied = $state(false);

	function toggleExpanded() {
		isExpanded = !isExpanded;
	}

	function getDataType(value: any): string {
		if (value === null) return 'null';
		if (value === undefined) return 'undefined';
		if (Array.isArray(value)) return 'array';
		return typeof value;
	}

	function isExpandable(value: any): boolean {
		return (typeof value === 'object' && value !== null) || Array.isArray(value);
	}

	function getValuePreview(value: any): string {
		if (Array.isArray(value)) {
			return `Array(${value.length})`;
		}
		if (typeof value === 'object' && value !== null) {
			const keys = Object.keys(value);
			return `Object(${keys.length})`;
		}
		return '';
	}

	function formatValue(value: any): string {
		if (typeof value === 'string') {
			return `"${value}"`;
		}
		if (value === null) {
			return 'null';
		}
		if (value === undefined) {
			return 'undefined';
		}
		return String(value);
	}

	async function copyToClipboard(value: any) {
		try {
			await navigator.clipboard.writeText(JSON.stringify(value, null, 2));
			copied = true;
			setTimeout(() => {
				copied = false;
			}, 2000);
		} catch (error) {
			console.error('Failed to copy to clipboard:', error);
		}
	}

	function getIndentation(level: number): string {
		return '  '.repeat(level);
	}
</script>

<div class="json-viewer" style="margin-left: {level * 16}px">
	{#if isExpandable(data)}
		<div class="json-node">
			<button
				onclick={toggleExpanded}
				class="expand-button"
				aria-label={isExpanded ? 'Collapse' : 'Expand'}
			>
				{#if isExpanded}
					<ChevronDown class="w-4 h-4" />
				{:else}
					<ChevronRight class="w-4 h-4" />
				{/if}
			</button>
			
			{#if parentKey}
				<span class="key">"{parentKey}":</span>
			{/if}
			
			<span class="bracket {getDataType(data)}">
				{Array.isArray(data) ? '[' : '{'}
			</span>
			
			{#if !isExpanded}
				<span class="preview">{getValuePreview(data)}</span>
				<span class="bracket {getDataType(data)}">
					{Array.isArray(data) ? ']' : '}'}
				</span>
			{/if}
			
			<button
				onclick={() => copyToClipboard(data)}
				class="copy-button"
				title="Copy to clipboard"
			>
				{#if copied}
					<Check class="w-3 h-3 text-green-500" />
				{:else}
					<Copy class="w-3 h-3" />
				{/if}
			</button>
		</div>

		{#if isExpanded}
			<div class="json-content">
				{#if Array.isArray(data)}
					{#each data as item, index}
						<div class="json-item">
							<span class="array-index">{index}:</span>
							{#if isExpandable(item)}
								<JsonViewer data={item} expanded={level < 2} level={level + 1} />
							{:else}
								<span class="value {getDataType(item)}">{formatValue(item)}</span>
								<button
									onclick={() => copyToClipboard(item)}
									class="copy-button inline"
									title="Copy value"
								>
									{#if copied}
										<Check class="w-3 h-3 text-green-500" />
									{:else}
										<Copy class="w-3 h-3" />
									{/if}
								</button>
							{/if}
							{#if index < data.length - 1}
								<span class="comma">,</span>
							{/if}
						</div>
					{/each}
				{:else}
					{#each Object.entries(data) as [key, value], index}
						<div class="json-item">
							{#if isExpandable(value)}
								<JsonViewer data={value} expanded={level < 2} level={level + 1} parentKey={key} />
							{:else}
								<span class="key">"{key}":</span>
								<span class="value {getDataType(value)}">{formatValue(value)}</span>
								<button
									onclick={() => copyToClipboard(value)}
									class="copy-button inline"
									title="Copy value"
								>
									{#if copied}
										<Check class="w-3 h-3 text-green-500" />
									{:else}
										<Copy class="w-3 h-3" />
									{/if}
								</button>
							{/if}
							{#if index < Object.entries(data).length - 1}
								<span class="comma">,</span>
							{/if}
						</div>
					{/each}
				{/if}
			</div>
			
			<div class="closing-bracket" style="margin-left: {level * 16}px">
				<span class="bracket {getDataType(data)}">
					{Array.isArray(data) ? ']' : '}'}
				</span>
			</div>
		{/if}
	{:else}
		<div class="json-simple">
			{#if parentKey}
				<span class="key">"{parentKey}":</span>
			{/if}
			<span class="value {getDataType(data)}">{formatValue(data)}</span>
			<button
				onclick={() => copyToClipboard(data)}
				class="copy-button inline"
				title="Copy value"
			>
				{#if copied}
					<Check class="w-3 h-3 text-green-500" />
				{:else}
					<Copy class="w-3 h-3" />
				{/if}
			</button>
		</div>
	{/if}
</div>

<style>
	.json-viewer {
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
		font-size: 14px;
		line-height: 1.4;
		color: #333;
		max-width: 100%;
		overflow-x: auto;
	}

	:global(.dark) .json-viewer {
		color: #e5e7eb;
	}

	.json-node {
		display: flex;
		align-items: flex-start;
		gap: 4px;
		margin: 2px 0;
		flex-wrap: wrap;
		max-width: 100%;
	}

	.json-item {
		display: flex;
		align-items: flex-start;
		gap: 4px;
		margin: 2px 0;
		padding-left: 16px;
		flex-wrap: wrap;
		max-width: calc(100% - 16px);
	}

	.json-simple {
		display: flex;
		align-items: flex-start;
		gap: 4px;
		margin: 2px 0;
		flex-wrap: wrap;
		max-width: 100%;
	}

	.json-content {
		margin: 4px 0;
		max-width: 100%;
		overflow-x: auto;
	}

	.closing-bracket {
		margin: 2px 0;
	}

	.expand-button {
		background: none;
		border: none;
		cursor: pointer;
		padding: 2px;
		border-radius: 2px;
		color: #6b7280;
		transition: all 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.expand-button:hover {
		background-color: #f3f4f6;
		color: #374151;
	}

	:global(.dark) .expand-button {
		color: #9ca3af;
	}

	:global(.dark) .expand-button:hover {
		background-color: #374151;
		color: #d1d5db;
	}

	.copy-button {
		background: none;
		border: none;
		cursor: pointer;
		padding: 2px;
		border-radius: 2px;
		color: #6b7280;
		transition: all 0.2s;
		opacity: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.copy-button.inline {
		margin-left: 4px;
	}

	.json-node:hover .copy-button,
	.json-item:hover .copy-button,
	.json-simple:hover .copy-button {
		opacity: 1;
	}

	.copy-button:hover {
		background-color: #f3f4f6;
		color: #374151;
	}

	:global(.dark) .copy-button:hover {
		background-color: #374151;
		color: #d1d5db;
	}

	.key {
		color: #0f766e;
		font-weight: 500;
		word-break: break-word;
		flex-shrink: 0;
	}

	:global(.dark) .key {
		color: #5eead4;
	}

	.array-index {
		color: #7c3aed;
		font-weight: 500;
		min-width: 20px;
		flex-shrink: 0;
	}

	:global(.dark) .array-index {
		color: #c4b5fd;
	}

	.value {
		font-weight: 500;
		word-break: break-word;
		max-width: 100%;
		overflow-wrap: break-word;
	}

	.value.string {
		color: #059669;
	}

	:global(.dark) .value.string {
		color: #34d399;
	}

	.value.number {
		color: #dc2626;
	}

	:global(.dark) .value.number {
		color: #f87171;
	}

	.value.boolean {
		color: #7c2d12;
	}

	:global(.dark) .value.boolean {
		color: #fed7aa;
	}

	.value.null,
	.value.undefined {
		color: #6b7280;
		font-style: italic;
	}

	:global(.dark) .value.null,
	:global(.dark) .value.undefined {
		color: #9ca3af;
	}

	.bracket {
		color: #374151;
		font-weight: 600;
		flex-shrink: 0;
	}

	:global(.dark) .bracket {
		color: #d1d5db;
	}

	.bracket.array {
		color: #7c3aed;
	}

	:global(.dark) .bracket.array {
		color: #c4b5fd;
	}

	.bracket.object {
		color: #0f766e;
	}

	:global(.dark) .bracket.object {
		color: #5eead4;
	}

	.preview {
		color: #6b7280;
		font-style: italic;
		margin: 0 4px;
		flex-shrink: 0;
	}

	:global(.dark) .preview {
		color: #9ca3af;
	}

	.comma {
		color: #374151;
		flex-shrink: 0;
	}

	:global(.dark) .comma {
		color: #d1d5db;
	}
</style> 