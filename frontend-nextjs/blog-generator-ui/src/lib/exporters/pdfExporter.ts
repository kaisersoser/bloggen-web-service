// Enhanced PDF export using styled HTML with perfect BlogViewModal visual matching
import { BlogData } from '@/types/blog';
import { generateEnhancedHTML } from './htmlExporter';
import { logger } from '@/lib/logger';

export async function generatePDF(blog: BlogData): Promise<void> {
  try {
    // Generate enhanced HTML with exact BlogViewModal styling
    const htmlContent = generateEnhancedHTML(blog);
    
    // Create a new window for PDF generation
    const printWindow = window.open('', '_blank', 'width=800,height=600');
    
    if (!printWindow) {
      throw new Error('Failed to open print window. Please check popup blockers.');
    }

    // Write the enhanced HTML content
    printWindow.document.write(htmlContent);
    printWindow.document.close();

    // Wait for content to load, then trigger print
    printWindow.onload = () => {
      // Small delay to ensure all content and images are loaded
      setTimeout(() => {
        try {
          // Focus the window and trigger print dialog
          printWindow.focus();
          printWindow.print();
          
          // Clean up - close the window after printing
          // Note: This will close after user completes or cancels print dialog
          printWindow.onafterprint = () => {
            printWindow.close();
          };
          
          // Fallback cleanup in case onafterprint doesn't fire
          setTimeout(() => {
            if (!printWindow.closed) {
              printWindow.close();
            }
          }, 5000);
          
        } catch (error) {
          logger.error('Print failed during PDF generation', error);
          printWindow.close();
        }
      }, 800); // Increased delay to ensure images load
    };

    // Error handling for failed window load
    setTimeout(() => {
      if (printWindow && !printWindow.closed && printWindow.document.readyState !== 'complete') {
        logger.warn('Print window taking too long to load, closing');
        printWindow.close();
      }
    }, 10000);

  } catch (error) {
    logger.error('PDF generation failed', error);
    throw new Error('Failed to generate PDF. Please try again.');
  }
}

// Alternative PDF generation using a PDF library (for future implementation)
export async function generatePDFBuffer(): Promise<Blob> {
  // This would use a library like jsPDF or Puppeteer for server-side PDF generation
  // For now, we'll use the print-to-PDF approach above
  
  throw new Error('PDF buffer generation not yet implemented. Use generatePDF() for print-to-PDF functionality.');
}