# MarkUI Frontend

A beautiful, modern Svelte 5 frontend for the MarkUI PDF conversion application. Convert PDFs to Markdown, JSON, and HTML with AI enhancement.

## Features

- **🎨 Modern UI**: Clean, responsive design with dark/light theme support
- **📄 PDF Upload**: Drag & drop or click to upload PDF files
- **🖼️ PDF Preview**: Visual page-by-page preview with selection
- **⚙️ Conversion Options**: All marker library options supported
- **🤖 AI Enhancement**: Multiple LLM service integrations
- **📱 Responsive**: Works on desktop, tablet, and mobile
- **🌙 Dark Mode**: Automatic theme switching with user preference
- **⚡ Real-time**: Live conversion progress and status updates

## Technology Stack

- **Framework**: Svelte 5 with SvelteKit
- **Styling**: Tailwind CSS 4 with custom components
- **Icons**: Lucide Svelte
- **Typography**: Tailwind Typography plugin
- **Build Tool**: Vite
- **Language**: TypeScript

## Getting Started

### Prerequisites

- Node.js 18+ 
- pnpm (recommended) or npm
- MarkUI Backend running on `http://localhost:8000`

### Installation

1. **Install dependencies**:
   ```bash
   pnpm install
   ```

2. **Start development server**:
   ```bash
   pnpm dev
   ```

3. **Open your browser**:
   Navigate to `http://localhost:5173`

### Building for Production

```bash
# Build the application
pnpm build

# Preview the production build
pnpm preview
```

## Project Structure

```
frontend/
├── src/
│   ├── lib/
│   │   ├── api.ts           # API client for backend communication
│   │   ├── stores.ts        # Svelte stores for state management
│   │   └── types.ts         # TypeScript type definitions
│   ├── routes/
│   │   ├── +layout.svelte   # Main layout with navigation
│   │   ├── +page.svelte     # Home page (PDF upload & management)
│   │   ├── convert/
│   │   │   └── +page.svelte # Conversion page with preview & options
│   │   └── settings/
│   │       └── +page.svelte # Settings page for configuration
│   ├── app.css              # Global styles and Tailwind imports
│   ├── app.html             # HTML template
│   └── app.d.ts             # TypeScript declarations
├── static/                  # Static assets
├── package.json             # Dependencies and scripts
└── README.md               # This file
```

## Features Overview

### Home Page (`/`)
- **PDF Upload**: Drag & drop or click to upload PDF files
- **PDF Management**: View uploaded PDFs with metadata
- **Quick Actions**: Convert or delete PDFs directly from the list

### Conversion Page (`/convert`)
- **PDF Preview**: Visual page thumbnails with selection
- **Page Selection**: Choose specific pages or select all
- **Output Format**: Choose between Markdown, JSON, or HTML
- **Marker Options**: All marker library options available:
  - Use LLM for enhanced accuracy
  - Force OCR on all text
  - Strip existing OCR text
  - Format lines using OCR
  - Redo inline math conversion
  - Disable image extraction
  - Paginate output
- **LLM Configuration**: Select and configure LLM services
- **Real-time Progress**: Live conversion status and progress
- **Result Display**: View converted content with proper formatting
- **Download**: Download converted files

### Settings Page (`/settings`)
- **Theme**: Light/Dark mode toggle
- **LLM Services**: Configure multiple AI services:
  - Google Gemini
  - OpenAI GPT
  - Anthropic Claude
  - Ollama (local)
  - Google Vertex AI
- **API Keys**: Secure API key management with visibility toggle
- **Default Options**: Set default conversion preferences
- **Service Configuration**: Model selection and endpoint configuration

## API Integration

The frontend communicates with the MarkUI backend through a comprehensive API client (`src/lib/api.ts`) that handles:

- **Authentication**: Error handling and response parsing
- **File Upload**: Multipart form data for PDF uploads
- **Real-time Updates**: Polling for conversion job status
- **Error Handling**: Comprehensive error messages and user feedback

## State Management

Global state is managed using Svelte stores (`src/lib/stores.ts`):

- **Theme**: Dark/light mode preference
- **User Settings**: API keys, default options, LLM configuration
- **Current PDF**: Selected PDF for conversion
- **Page Selection**: Selected pages for conversion
- **Conversion Options**: All marker library options
- **Loading States**: UI loading indicators
- **Error Handling**: Global error messages

## Styling

The application uses Tailwind CSS 4 with:

- **Custom Components**: Reusable UI components
- **Dark Mode**: Automatic theme switching
- **Typography**: Enhanced prose styling for converted content
- **Responsive Design**: Mobile-first approach
- **Animations**: Smooth transitions and loading states

## Development

### Code Style

- **TypeScript**: Strict type checking enabled
- **ESLint**: Code linting with Svelte-specific rules
- **Prettier**: Code formatting with Tailwind plugin
- **Svelte 5**: Latest Svelte features and syntax

### Available Scripts

```bash
# Development
pnpm dev          # Start development server
pnpm dev --open   # Start development server and open browser

# Building
pnpm build        # Build for production
pnpm preview      # Preview production build

# Code Quality
pnpm check        # Type checking
pnpm check:watch  # Type checking in watch mode
pnpm lint         # Run ESLint
pnpm format       # Format code with Prettier
```

### Environment Configuration

The frontend expects the backend to be running on `http://localhost:8000`. To change this, update the `API_BASE_URL` in `src/lib/api.ts`.

## Browser Support

- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile**: iOS Safari 14+, Chrome Mobile 90+
- **Features**: ES2020, CSS Grid, Flexbox, CSS Custom Properties

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see the main project LICENSE file for details.

## Related

- [MarkUI Backend](../backend/README.md) - FastAPI backend
- [Marker Library](https://github.com/VikParuchuri/marker) - PDF conversion engine
