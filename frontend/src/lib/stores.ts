import { writable, derived, get } from 'svelte/store';
import type { 
	UserSettings, 
	PDFDocument, 
	ConversionJob, 
	LLMServiceInfo,
	OutputFormat,
	LLMServiceTestRequest,
	LLMServiceTestResponse
} from './types';
import { MarkUIAPI } from './api';
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

// User settings store
export const userSettings = writable<UserSettings | null>(null);

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
export const conversionDefaultsLoaded = writable(false);

// Error handling
export const error = writable<string | null>(null);

// PDF list store
export const pdfList = writable<PDFDocument[]>([]);

// Conversion jobs store
export const conversionJobs = writable<ConversionJob[]>([]);

// LLM services store
export const llmServices = writable<LLMServiceInfo[]>([]);
export const configuredLLMServices = writable<LLMServiceInfo[]>([]);

// Ollama models store
export const ollamaModels = writable<string[]>([]);

// Current conversion result
export const currentResult = writable<{
	job: ConversionJob;
	content?: string;
	images?: string[];
} | null>(null);

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
			
			// Save to localStorage instead of backend
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
		selectedPages.set(new Set()); // Clear selected pages when switching PDFs
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
	updateConversionOption<K extends keyof typeof conversionOptions>(
		key: K, 
		value: any
	) {
		conversionOptions.update(options => ({
			...options,
			[key]: value
		}));
	},

	async resetConversionOptions() {
		try {
			const defaults = await MarkUIAPI.getConversionDefaults();
			conversionOptions.set({
				output_format: defaults.output_format as OutputFormat,
				use_llm: defaults.use_llm,
				force_ocr: defaults.force_ocr,
				strip_existing_ocr: defaults.strip_existing_ocr,
				format_lines: defaults.format_lines,
				redo_inline_math: defaults.redo_inline_math,
				disable_image_extraction: defaults.disable_image_extraction,
				paginate_output: defaults.paginate_output,
				llm_service: defaults.llm_service || undefined,
				llm_model: undefined
			});
		} catch (err) {
			// Fallback to hardcoded defaults if API call fails
			conversionOptions.set({
				output_format: 'markdown' as OutputFormat,
				use_llm: false,
				force_ocr: false,
				strip_existing_ocr: false,
				format_lines: false,
				redo_inline_math: false,
				disable_image_extraction: false,
				paginate_output: false,
				llm_service: undefined,
				llm_model: undefined
			});
		}
	},

	// API actions
	async loadUserSettings() {
		try {
			isLoading.set(true);
			const settings = await MarkUIAPI.getUserSettings();
			console.log('Loaded user settings:', settings);
			userSettings.set(settings);
			// Theme is now managed locally via localStorage, not from backend
		} catch (err) {
			actions.setError(`Failed to load settings: ${err}`);
		} finally {
			isLoading.set(false);
		}
	},

	async updateSettings(updates: Partial<UserSettings>) {
		try {
			isLoading.set(true);
			console.log('Updating settings:', updates);
			
			// Remove theme from updates since it's managed locally
			const { theme: _, ...backendUpdates } = updates;
			
			const updatedSettings = await MarkUIAPI.updateUserSettings(backendUpdates);
			console.log('Updated settings response:', updatedSettings);
			userSettings.set(updatedSettings);
			// Theme is now managed locally via localStorage, not from backend
		} catch (err) {
			actions.setError(`Failed to update settings: ${err}`);
		} finally {
			isLoading.set(false);
		}
	},

	async loadPDFList() {
		try {
			isLoading.set(true);
			const response = await MarkUIAPI.listPDFs();
			pdfList.set(response.pdfs);
		} catch (err) {
			actions.setError(`Failed to load PDFs: ${err}`);
		} finally {
			isLoading.set(false);
		}
	},

	async loadConversionJobs() {
		try {
			const response = await MarkUIAPI.listConversionJobs();
			conversionJobs.set(response.jobs);
		} catch (err) {
			actions.setError(`Failed to load conversion jobs: ${err}`);
		}
	},

	async loadLLMServices() {
		try {
			const response = await MarkUIAPI.getLLMServices();
			llmServices.set(response.services);
		} catch (err) {
			actions.setError(`Failed to load LLM services: ${err}`);
		}
	},

	async loadConfiguredLLMServices() {
		try {
			const response = await MarkUIAPI.getConfiguredLLMServices();
			configuredLLMServices.set(response.services);
		} catch (err) {
			actions.setError(`Failed to load configured LLM services: ${err}`);
		}
	},

	async testLLMServiceConnection(testRequest: LLMServiceTestRequest): Promise<LLMServiceTestResponse> {
		try {
			return await MarkUIAPI.testLLMServiceConnection(testRequest);
		} catch (err) {
			throw new Error(`Failed to test LLM service connection: ${err}`);
		}
	},

	async loadOllamaModels(baseUrl: string) {
		try {
			const response = await MarkUIAPI.getOllamaModels(baseUrl);
			ollamaModels.set(response.models);
			return response.models;
		} catch (err) {
			ollamaModels.set([]);
			throw new Error(`Failed to load Ollama models: ${err}`);
		}
	},

	async loadConversionDefaults() {
		try {
			const defaults = await MarkUIAPI.getConversionDefaults();
			conversionOptions.set({
				output_format: defaults.output_format as OutputFormat,
				use_llm: defaults.use_llm,
				force_ocr: defaults.force_ocr,
				strip_existing_ocr: defaults.strip_existing_ocr,
				format_lines: defaults.format_lines,
				redo_inline_math: defaults.redo_inline_math,
				disable_image_extraction: defaults.disable_image_extraction,
				paginate_output: defaults.paginate_output,
				llm_service: defaults.llm_service || undefined,
				llm_model: undefined
			});
			conversionDefaultsLoaded.set(true);
		} catch (err) {
			console.error('Failed to load conversion defaults:', err);
			actions.setError(`Failed to load conversion defaults: ${err}`);
			conversionDefaultsLoaded.set(true); // Set to true even on error to prevent infinite loading
		}
	}
};

// Initialize stores on app start
if (typeof window !== 'undefined') {
	// Load initial data with error handling
	actions.loadUserSettings().catch(console.error);
	actions.loadLLMServices().catch(console.error);
	actions.loadConfiguredLLMServices().catch(console.error);
	actions.loadConversionDefaults().catch(console.error);
} 