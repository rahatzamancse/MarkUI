import { writable, derived, get } from 'svelte/store';
import type { 
	PDFDocument, 
	ConversionJob, 
	OutputFormat
} from './types';
import { browser } from '$app/environment';

// Theme store with localStorage persistence
function createThemeStore() {
	// Initialize from localStorage or default to 'light'
	let initialTheme: 'light' | 'dark' = 'light';
	
	if (browser) {
		try {
			const stored = localStorage.getItem('theme');
			console.log('Reading theme from localStorage:', stored);
			if (stored === 'dark' || stored === 'light') {
				initialTheme = stored;
			}
		} catch (error) {
			console.error('Error reading theme from localStorage:', error);
		}
	}
	
	console.log('Initializing theme store with:', initialTheme);
	const { subscribe, set, update } = writable<'light' | 'dark'>(initialTheme);

	return {
		subscribe,
		set: (value: 'light' | 'dark') => {
			console.log('Setting theme to:', value);
			if (browser) {
				try {
					localStorage.setItem('theme', value);
					console.log('Saved theme to localStorage:', value);
				} catch (error) {
					console.error('Error saving theme to localStorage:', error);
				}
			}
			set(value);
		},
		update
	};
}

export const theme = createThemeStore();

// Add debugging to theme changes
theme.subscribe(value => {
	console.log('Theme store changed to:', value);
});

// Current PDF store
export const currentPDF = writable<PDFDocument | null>(null);

// Selected pages store
export const selectedPages = writable<Set<number>>(new Set());

// Conversion options store
export const conversionOptions = writable({
	output_format: 'markdown' as OutputFormat,
	use_llm: false,
	force_ocr: false,
	strip_existing_ocr: false,
	format_lines: false,
	redo_inline_math: false,
	disable_image_extraction: false,
	paginate_output: false,
	llm_service: undefined as string | undefined,
	llm_model: undefined as string | undefined
});

// Loading states
export const isLoading = writable(false);
export const uploadProgress = writable(0);

// Error handling
export const error = writable<string | null>(null);

// Conversion jobs store
export const conversionJobs = writable<ConversionJob[]>([]);

// Current conversion result
export const currentResult = writable<{
	job: ConversionJob;
	content?: string;
	images?: string[];
} | null>(null);

// LLM Configuration (session-only, no persistence)
export const llmConfig = writable({
	gemini_api_key: '',
	openai_api_key: '',
	claude_api_key: '',
	ollama_base_url: 'http://localhost:11434',
	ollama_model: 'llama3.2:latest',
	openai_model: 'gpt-4o',
	openai_base_url: '',
	claude_model_name: 'claude-3-sonnet-20240229',
	vertex_project_id: '',
	default_llm_service: ''
});

// Derived stores
export const isDarkMode = derived(theme, ($theme) => {
	const result = $theme === 'dark';
	console.log('isDarkMode derived:', $theme, '->', result);
	return result;
});

export const hasSelectedPages = derived(selectedPages, ($selectedPages) => $selectedPages.size > 0);

export const canStartConversion = derived(
	[currentPDF, selectedPages, conversionOptions],
	([$currentPDF, $selectedPages, $conversionOptions]) => {
		return $currentPDF !== null && ($selectedPages.size > 0 || !$selectedPages.size);
	}
);

// Actions
export const actions = {
	// Theme actions
	async toggleTheme() {
		try {
			const currentTheme = get(theme);
			const newTheme = currentTheme === 'light' ? 'dark' : 'light';
			console.log('Toggle theme:', currentTheme, '->', newTheme);
			theme.set(newTheme);
		} catch (err) {
			actions.setError(`Failed to toggle theme: ${err}`);
		}
	},

	setTheme(newTheme: 'light' | 'dark') {
		console.log('Set theme:', newTheme);
		theme.set(newTheme);
	},

	// Error handling
	setError(message: string | null) {
		error.set(message);
		if (message) {
			// Auto-clear error after 5 seconds
			setTimeout(() => error.set(null), 5000);
		}
	},

	clearError() {
		error.set(null);
	},

	// Loading states
	setLoading(loading: boolean) {
		isLoading.set(loading);
	},

	// PDF actions
	selectPDF(pdf: PDFDocument) {
		currentPDF.set(pdf);
		// Select all pages by default when switching PDFs
		const allPages = new Set<number>();
		for (let i = 1; i <= pdf.total_pages; i++) {
			allPages.add(i);
		}
		selectedPages.set(allPages);
	},

	clearCurrentPDF() {
		currentPDF.set(null);
		selectedPages.set(new Set());
	},

	// Page selection actions
	togglePage(pageNumber: number) {
		selectedPages.update(pages => {
			const newPages = new Set(pages);
			if (newPages.has(pageNumber)) {
				newPages.delete(pageNumber);
			} else {
				newPages.add(pageNumber);
			}
			return newPages;
		});
	},

	selectAllPages(totalPages: number) {
		const allPages = new Set<number>();
		for (let i = 1; i <= totalPages; i++) {
			allPages.add(i);
		}
		selectedPages.set(allPages);
	},

	clearSelectedPages() {
		selectedPages.set(new Set());
	},

	selectPageRange(start: number, end: number) {
		const rangePages = new Set<number>();
		for (let i = start; i <= end; i++) {
			rangePages.add(i);
		}
		selectedPages.update(pages => new Set([...pages, ...rangePages]));
	},

	// Conversion options actions
	updateConversionOption(key: string, value: any) {
		conversionOptions.update(options => ({
			...options,
			[key]: value
		}));
	},

	// LLM Config actions
	updateLLMConfig(key: string, value: any) {
		llmConfig.update(config => ({
			...config,
			[key]: value
		}));
	}
}; 