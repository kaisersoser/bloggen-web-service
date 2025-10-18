// Simple Word document export that actually works
import { BlogData } from '../../types/blog';
import { Document, Packer, Paragraph, TextRun } from 'docx';
import { logger } from '@/lib/logger';

export async function generateWordDocument(blog: BlogData): Promise<Blob> {
  logger.info('Starting Word document generation', { topic: blog.topic });
  
  try {
    // Validate input
    if (!blog || !blog.topic) {
      throw new Error('Invalid blog data provided');
    }
    
    // Create a simple document to test basic functionality
    const doc = new Document({
      sections: [{
        children: [
          new Paragraph({
            children: [
              new TextRun({
                text: blog.topic || 'Blog Post',
                bold: true,
                size: 28,
              }),
            ],
          }),
          new Paragraph({
            children: [
              new TextRun({
                text: '\n',
              }),
            ],
          }),
          new Paragraph({
            children: [
              new TextRun({
                text: blog.content || 'No content available',
              }),
            ],
          }),
          new Paragraph({
            children: [
              new TextRun({
                text: '\n',
              }),
            ],
          }),
          new Paragraph({
            children: [
              new TextRun({
                text: `Created: ${new Date(blog.createdAt).toLocaleDateString()}`,
                size: 20,
                italics: true,
              }),
            ],
          }),
        ],
      }],
    });

    logger.info('Document structure created, generating buffer');
    const buffer = await Packer.toBuffer(doc);
    logger.info('Buffer generated successfully', { size: buffer.byteLength });
    
    // Convert buffer to Uint8Array for blob compatibility
    const uint8Array = new Uint8Array(buffer);
    const blob = new Blob([uint8Array], { 
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
    });
    
    logger.info('Word document blob created successfully', { size: blob.size });
    return blob;
    
  } catch (error) {
    logger.error('Error generating Word document', error);
    throw new Error(`Word document generation failed: ${error instanceof Error ? error.message : String(error)}`);
  }
}