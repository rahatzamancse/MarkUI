// API Types based on backend schemas

export interface PDFDocument {
	id: number;
	filename: string;
	original_filename: string;
	file_size: number;
	total_pages: number;
	upload_timestamp: string;
	title?: string;
	author?: string;
	subject?: string;
	creator?: string;
	producer?: string;
	creation_date?: string;
	modification_date?: string;
	metadata?: Record<string, any>;
	created_at: string;
}

export interface PDFUploadResponse extends PDFDocument {
	preview_images: string[];
}

export enum ConversionStatus {
	PENDING = 'pending',
	PROCESSING = 'processing',
	COMPLETED = 'completed',
	FAILED = 'failed'
}

export enum OutputFormat {
	MARKDOWN = 'markdown',
	JSON = 'json',
	HTML = 'html'
}

export interface ConversionJobCreate {
	pdf_document_id: number;
	output_format: OutputFormat;
	selected_pages?: number[];
	use_llm: boolean;
	force_ocr: boolean;
	strip_existing_ocr: boolean;
	format_lines: boolean;
	redo_inline_math: boolean;
	disable_image_extraction: boolean;
	paginate_output: boolean;
	
	// Performance & Quality Options
	lowres_image_dpi?: number;
	highres_image_dpi?: number;
	layout_batch_size?: number;
	detection_batch_size?: number;
	recognition_batch_size?: number;
	
	// OCR & Text Processing Options
	languages?: string[];
	ocr_task_name?: string;
	disable_ocr_math?: boolean;
	keep_chars?: boolean;
	
	// Layout & Structure Options
	force_layout_block?: string;
	column_gap_ratio?: number;
	gap_threshold?: number;
	list_gap_threshold?: number;
	
	// Table Processing Options
	detect_boxes?: boolean;
	table_rec_batch_size?: number;
	max_table_rows?: number;
	max_rows_per_batch?: number;
	
	// Section & Header Processing
	level_count?: number;
	merge_threshold?: number;
	default_level?: number;
	
	// Advanced Processing Options
	min_equation_height?: number;
	equation_batch_size?: number;
	inlinemath_min_ratio?: number;
	
	// Output Control Options
	page_separator?: string;
	extract_images?: boolean;
	
	// Debug Options
	debug?: boolean;
	debug_layout_images?: boolean;
	debug_pdf_images?: boolean;
	debug_json?: boolean;
	debug_data_folder?: string;
	
	// LLM service configuration
	llm_service?: string;
	llm_model?: string;
	
	// LLM Processing Options
	max_concurrency?: number;
	confidence_threshold?: number;
	
	// Per-job API keys (optional, will fallback to settings if not provided)
	gemini_api_key?: string;
	openai_api_key?: string;
	claude_api_key?: string;
	
	// Service-specific LLM configuration
	ollama_base_url?: string;
	openai_base_url?: string;
	claude_model_name?: string;
	vertex_project_id?: string;
	
	// Service-specific model names  
	openai_model?: string;
	ollama_model?: string;
	gemini_model_name?: string;
}

export interface ConversionJob {
	id: string;
	pdf_document_id: number;
	status: ConversionStatus;
	output_format: OutputFormat;
	selected_pages?: number[];
	progress: number;
	error_message?: string;
	created_at: string;
	started_at?: string;
	completed_at?: string;
	use_llm: boolean;
	force_ocr: boolean;
	strip_existing_ocr: boolean;
	format_lines: boolean;
	redo_inline_math: boolean;
	disable_image_extraction: boolean;
	paginate_output: boolean;
	
	// Performance & Quality Options
	lowres_image_dpi?: number;
	highres_image_dpi?: number;
	layout_batch_size?: number;
	detection_batch_size?: number;
	recognition_batch_size?: number;
	
	// OCR & Text Processing Options
	languages?: string[];
	ocr_task_name?: string;
	disable_ocr_math?: boolean;
	keep_chars?: boolean;
	
	// Layout & Structure Options
	force_layout_block?: string;
	column_gap_ratio?: number;
	gap_threshold?: number;
	list_gap_threshold?: number;
	
	// Table Processing Options
	detect_boxes?: boolean;
	table_rec_batch_size?: number;
	max_table_rows?: number;
	max_rows_per_batch?: number;
	
	// Section & Header Processing
	level_count?: number;
	merge_threshold?: number;
	default_level?: number;
	
	// Advanced Processing Options
	min_equation_height?: number;
	equation_batch_size?: number;
	inlinemath_min_ratio?: number;
	
	// Output Control Options
	page_separator?: string;
	extract_images?: boolean;
	
	// Debug Options
	debug?: boolean;
	debug_layout_images?: boolean;
	debug_pdf_images?: boolean;
	debug_json?: boolean;
	debug_data_folder?: string;
	
	// LLM service configuration
	llm_service?: string;
	llm_model?: string;
	
	// LLM Processing Options
	max_concurrency?: number;
	confidence_threshold?: number;
}

export interface ConversionJobListResponse {
	jobs: ConversionJob[];
	total: number;
	page: number;
	per_page: number;
	pages: number;
}

export interface ConversionResult {
	job: ConversionJob;
	content?: string;
	images?: string[];
}

export interface LLMServiceTestRequest {
	service_name: string;
	gemini_api_key?: string;
	openai_api_key?: string;
	claude_api_key?: string;
	ollama_base_url?: string;
	ollama_model?: string;
	openai_model?: string;
	openai_base_url?: string;
	claude_model_name?: string;
	vertex_project_id?: string;
}

export interface LLMServiceTestResponse {
	success: boolean;
	message: string;
	response_time_ms?: number;
}

export interface ServerConfigResponse {
	// API key availability (boolean flags, not the actual keys)
	has_gemini_api_key: boolean;
	has_openai_api_key: boolean;
	has_claude_api_key: boolean;
	
	// Default model configurations from environment
	default_openai_model?: string;
	default_openai_base_url?: string;
	default_claude_model_name?: string;
	default_ollama_base_url?: string;
	default_ollama_model?: string;
	default_vertex_project_id?: string;
}

// UI State Types
export interface AppState {
	theme: 'light' | 'dark';
	currentPDF?: PDFDocument;
	selectedPages: Set<number>;
	conversionOptions: ConversionJobCreate;
	isLoading: boolean;
	error?: string;
}

export interface PagePreview {
	pageNumber: number;
	imageUrl: string;
	selected: boolean;
} 