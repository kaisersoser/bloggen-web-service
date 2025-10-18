// Enhanced blog export utilities with perfect BlogViewModal visual matching
// Provides consistent formatting across all export formats
import { BlogData } from '@/types/blog';
import { generateEnhancedHTML } from './htmlExporter';
import { generatePDF } from './pdfExporter';
import { generateWordDocument } from './wordExporter';
import { logger } from '@/lib/logger';

export type BlogExportFormat = 'md' | 'html' | 'pdf' | 'docx' | 'rtf';

interface ExportOptions { format: BlogExportFormat; blog: BlogData; }

export async function exportBlog({ format, blog }: ExportOptions): Promise<void> {
	if (!blog.content) {
		throw new Error('No blog content available for export');
	}
	
	const filenameBase = sanitizeFilename(`${blog.topic}_blog`);
	
	try {
		switch (format) {
			case 'md':
				await exportEnhancedMarkdown(blog, filenameBase);
				break;
			case 'html':
				await exportEnhancedHTML(blog, filenameBase);
				break;
			case 'pdf':
				await generatePDF(blog);
				break;
			case 'docx':
				await exportWordDocument(blog, filenameBase);
				break;
			case 'rtf':
				await exportEnhancedRTF(blog, filenameBase);
				break;
			default:
				throw new Error(`Unsupported export format: ${format}`);
		}
		} catch (error) {
			logger.error(`Export failed for format ${format}`, error);
		throw new Error(`Failed to export blog as ${format.toUpperCase()}. Please try again.`);
	}
}

export const blogExportFormats: { format: BlogExportFormat; label: string }[] = [
	{ format: 'md', label: 'Markdown (.md)' },
	{ format: 'html', label: 'HTML (.html)' },
	{ format: 'pdf', label: 'PDF (Print)' },
	{ format: 'docx', label: 'Word (.docx)' },
	{ format: 'rtf', label: 'RTF (.rtf)' }
];

// Enhanced export functions
async function exportEnhancedHTML(blog: BlogData, filenameBase: string): Promise<void> {
	const htmlContent = generateEnhancedHTML(blog);
	downloadText(htmlContent, `${filenameBase}.html`, 'text/html');
}

async function exportWordDocument(blog: BlogData, filenameBase: string): Promise<void> {
	try {
		logger.info('Generating Word document for blog export', { topic: blog.topic });
		const wordBlob = await generateWordDocument(blog);
		logger.info('Word document generated successfully', { size: wordBlob.size, topic: blog.topic });
		downloadBlob(wordBlob, `${filenameBase}.docx`);
		logger.info('Word document download initiated', { filename: `${filenameBase}.docx` });
	} catch (error) {
		logger.error('Word document export failed', error);
		// Show user-friendly error message
		alert(`Failed to generate Word document: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`);
		throw error;
	}
}

async function exportEnhancedMarkdown(blog: BlogData, filenameBase: string): Promise<void> {
	const enhancedMarkdown = generateEnhancedMarkdown(blog);
	downloadText(enhancedMarkdown, `${filenameBase}.md`, 'text/markdown');
}

async function exportEnhancedRTF(blog: BlogData, filenameBase: string): Promise<void> {
	const rtfContent = generateEnhancedRTF(blog);
	downloadText(rtfContent, `${filenameBase}.rtf`, 'application/rtf');
}

// Enhanced Markdown with frontmatter and metadata
function generateEnhancedMarkdown(blog: BlogData): string {
	const createdAt = new Date(blog.createdAt).toISOString();
	const completedAt = blog.completedAt ? new Date(blog.completedAt).toISOString() : null;
	
	let markdown = `---
title: "${blog.topic}"
created_at: "${createdAt}"
${completedAt ? `completed_at: "${completedAt}"` : ''}
status: "${blog.status}"
${blog.heroImageUrl ? `hero_image: "${blog.heroImageUrl}"` : ''}
format: "A4"
styling: "BlogViewModal"
export_date: "${new Date().toISOString()}"
---

`;

	// Add hero image if available
	if (blog.heroImageUrl) {
		markdown += `![${blog.topic} hero image](${blog.heroImageUrl} "${blog.topic} - Hero image – AI generated / Unsplash fallback")\n\n`;
	}

	// Add main content
	markdown += blog.content || 'No content available';

	// Add footer metadata
	markdown += `\n\n---

**Blog Metadata:**
- Created: ${new Date(blog.createdAt).toLocaleDateString()}
${completedAt ? `- Completed: ${new Date(blog.completedAt!).toLocaleDateString()}` : ''}
- Status: ${blog.status}
- Export Date: ${new Date().toLocaleDateString()}
`;

	return markdown;
}

// Enhanced RTF with basic styling
function generateEnhancedRTF(blog: BlogData): string {
	const title = escapeRtf(blog.topic || 'Blog Post');
	const content = escapeRtf(blog.content || 'No content available');
	const createdAt = new Date(blog.createdAt).toLocaleDateString();
	const completedAt = blog.completedAt ? new Date(blog.completedAt).toLocaleDateString() : null;

	// RTF with better formatting
	let rtf = `{\\rtf1\\ansi\\deff0
{\\fonttbl {\\f0 Georgia;}{\\f1 Times New Roman;}}
{\\colortbl;\\red51\\green51\\blue51;\\red59\\green130\\blue246;\\red17\\green24\\blue39;}

\\paperw11906\\paperh16838\\margl1134\\margr1134\\margt1134\\margb1134

`;

	// Title
	rtf += `{\\f0\\fs36\\b\\cf3 ${title}}\\par\\par\n`;

	// Hero image placeholder (RTF has limited image support)
	if (blog.heroImageUrl) {
		rtf += `{\\f0\\fs18\\i Hero Image: ${escapeRtf(blog.heroImageUrl)}}\\par\\par\n`;
	}

	// Content with basic formatting
	const formattedContent = content
		.replace(/\n\n/g, '\\par\\par\n')
		.replace(/\n/g, '\\par\n')
		.replace(/\*\*(.*?)\*\*/g, '{\\b $1}')
		.replace(/\*(.*?)\*/g, '{\\i $1}')
		.replace(/`(.*?)`/g, '{\\f1\\fs20 $1}');

	rtf += `{\\f0\\fs24\\cf1 ${formattedContent}}\\par\\par\n`;

	// Footer
	rtf += `\\pard\\brdrb\\brdrs\\brdrw10\\brsp20\\par\n`;
	rtf += `{\\f0\\fs18\\cf1 Created: ${createdAt}`;
	if (completedAt) {
		rtf += ` | Completed: ${completedAt}`;
	}
	rtf += ` | Status: ${blog.status}}\\par\n`;

	rtf += '}';
	return rtf;
}

// Utility functions
function sanitizeFilename(name: string): string { 
	return name.replace(/[^a-z0-9]/gi, '_').toLowerCase(); 
}

function downloadText(content: string, filename: string, mimeType: string): void { 
	const blob = new Blob([content], { type: mimeType }); 
	downloadBlob(blob, filename);
}

function downloadBlob(blob: Blob, filename: string): void {
	try {
		logger.info('Downloading blob for export', { filename, size: blob.size, type: blob.type });
		const url = URL.createObjectURL(blob); 
		const a = document.createElement('a'); 
		a.href = url; 
		a.download = filename;
		a.style.display = 'none';
		document.body.appendChild(a); 
		a.click(); 
		document.body.removeChild(a); 
		URL.revokeObjectURL(url);
		logger.info('Download triggered successfully', { filename });
	} catch (error) {
		logger.error('Download failed', error);
		throw new Error(`Download failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
	}
}

function escapeRtf(str: string): string { 
	return str.replace(/[\\{}]/g, m => `\\${m}`); 
}
