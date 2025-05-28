// API Types based on backend schemas

export interface PDFDocument {
	id: number;
	filename: string;
	original_filename: string;
	file_size: number;
	total_pages: number;
	metadata: Record<string, any>;
	is_processed: boolean;
	created_at: string;
}

export interface PDFUploadResponse extends PDFDocument {
	preview_images: string[];
}

export interface PDFListResponse {
	pdfs: PDFDocument[];
	total: number;
	page: number;
	per_page: number;
}

export enum ConversionStatus {
	PENDING = 'pending',
	PROCESSING = 'processing',
	COMPLETED = 'completed',
	FAILED = 'failed',
	CANCELLED = 'cancelled'
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
	use_llm?: boolean;
	force_ocr?: boolean;
	strip_existing_ocr?: boolean;
	format_lines?: boolean;
	redo_inline_math?: boolean;
	disable_image_extraction?: boolean;
	paginate_output?: boolean;
	llm_service?: string;
	llm_model?: string;
}

export interface ConversionJob {
	id: number;
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
	llm_service?: string;
	llm_model?: string;
	status: ConversionStatus;
	progress: number;
	output_file_path?: string;
	output_metadata?: Record<string, any>;
	error_message?: string;
	created_at: string;
	started_at?: string;
	completed_at?: string;
}

export interface ConversionJobListResponse {
	jobs: ConversionJob[];
	total: number;
	page: number;
	per_page: number;
}

export interface ConversionResult {
	job: ConversionJob;
	content?: string;
	images?: string[];
}

export interface UserSettings {
	id: number;
	theme: 'light' | 'dark';
	default_llm_service?: string;
	has_gemini_api_key: boolean;
	has_openai_api_key: boolean;
	has_claude_api_key: boolean;
	ollama_base_url?: string;
	ollama_model?: string;
	openai_model?: string;
	openai_base_url?: string;
	claude_model_name?: string;
	vertex_project_id?: string;
	default_output_format: string;
	default_use_llm: boolean;
	default_force_ocr: boolean;
	default_format_lines: boolean;
	additional_settings?: Record<string, any>;
}

export interface UserSettingsUpdate {
	theme?: 'light' | 'dark';
	default_llm_service?: string;
	gemini_api_key?: string;
	openai_api_key?: string;
	claude_api_key?: string;
	ollama_base_url?: string;
	ollama_model?: string;
	openai_model?: string;
	openai_base_url?: string;
	claude_model_name?: string;
	vertex_project_id?: string;
	default_output_format?: string;
	default_use_llm?: boolean;
	default_force_ocr?: boolean;
	default_format_lines?: boolean;
	additional_settings?: Record<string, any>;
}

export interface LLMServiceInfo {
	name: string;
	display_name: string;
	requires_api_key: boolean;
	models?: string[];
	description: string;
}

export interface LLMServicesResponse {
	services: LLMServiceInfo[];
}

export interface LLMServiceTestRequest {
	service_name: string;
	// API keys for testing (optional, will fallback to settings if not provided)
	gemini_api_key?: string;
	openai_api_key?: string;
	claude_api_key?: string;
	// Service-specific settings
	ollama_base_url?: string;
	ollama_model?: string;
	openai_model?: string;
	openai_base_url?: string;
	claude_model_name?: string;
	vertex_project_id?: string;
}

export interface LLMServiceTestResponse {
	service_name: string;
	success: boolean;
	message: string;
	response_time_ms?: number;
	error_details?: string;
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