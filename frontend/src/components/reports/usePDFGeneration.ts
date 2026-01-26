import { useState, useCallback } from 'react';

// Note: Install these dependencies before using:
// npm install jspdf html2canvas

export interface PDFGenerationOptions {
    filename?: string;
    quality?: number;
    scale?: number;
    margin?: number;
}

export interface PDFGenerationResult {
    success: boolean;
    error?: string;
    blob?: Blob;
}

export function usePDFGeneration() {
    const [isGenerating, setIsGenerating] = useState(false);
    const [progress, setProgress] = useState(0);

    const generatePDF = useCallback(async (
        element: HTMLElement,
        options: PDFGenerationOptions = {}
    ): Promise<PDFGenerationResult> => {
        const {
            filename = 'informe-vng.pdf',
            quality = 2,
            scale = 2,
            margin = 10
        } = options;

        setIsGenerating(true);
        setProgress(0);

        try {
            // Dynamic imports to avoid build errors if not installed
            const [jsPDFModule, html2canvasModule] = await Promise.all([
                import('jspdf'),
                import('html2canvas')
            ]);

            const jsPDF = jsPDFModule.default;
            const html2canvas = html2canvasModule.default;

            setProgress(20);

            // Render element to canvas
            const canvas = await html2canvas(element, {
                scale,
                useCORS: true,
                logging: false,
                backgroundColor: '#ffffff'
            });

            setProgress(60);

            // Calculate dimensions
            const imgWidth = 210 - (margin * 2); // A4 width in mm minus margins
            const pageHeight = 297 - (margin * 2); // A4 height in mm minus margins
            const imgHeight = (canvas.height * imgWidth) / canvas.width;
            const imgData = canvas.toDataURL('image/jpeg', quality);

            setProgress(80);

            // Create PDF
            const pdf = new jsPDF('p', 'mm', 'a4');
            let heightLeft = imgHeight;
            let position = margin;
            let page = 1;

            // Add first page
            pdf.addImage(imgData, 'JPEG', margin, position, imgWidth, imgHeight);
            heightLeft -= pageHeight;

            // Add additional pages if needed
            while (heightLeft > 0) {
                position = heightLeft - imgHeight + margin;
                pdf.addPage();
                pdf.addImage(imgData, 'JPEG', margin, position, imgWidth, imgHeight);
                heightLeft -= pageHeight;
                page++;
            }

            setProgress(100);

            // Generate blob for download
            const blob = pdf.output('blob');

            // Trigger download
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            setIsGenerating(false);
            return { success: true, blob };

        } catch (error) {
            setIsGenerating(false);
            const errorMessage = error instanceof Error ? error.message : 'Error generating PDF';

            // Check if it's a module not found error
            if (errorMessage.includes('Cannot find module') || errorMessage.includes('Failed to resolve')) {
                return {
                    success: false,
                    error: 'PDF dependencies not installed. Run: npm install jspdf html2canvas'
                };
            }

            return { success: false, error: errorMessage };
        }
    }, []);

    const generateFromSections = useCallback(async (
        containerRef: React.RefObject<HTMLElement>,
        options: PDFGenerationOptions = {}
    ): Promise<PDFGenerationResult> => {
        if (!containerRef.current) {
            return { success: false, error: 'Container element not found' };
        }

        return generatePDF(containerRef.current, options);
    }, [generatePDF]);

    return {
        generatePDF,
        generateFromSections,
        isGenerating,
        progress
    };
}

// Export default reference values for rendering
export const REFERENCE_RANGES = {
    saccade: {
        latency: { min: 150, max: 250, unit: 'ms' },
        velocity: { min: 300, max: 600, unit: '°/s' },
        accuracy: { min: 80, max: 100, unit: '%' }
    },
    pursuit: {
        gain: { min: 0.8, max: 1.0, unit: '' }
    },
    caloric: {
        spv: { min: 6, max: 80, unit: '°/s' },
        uw: { min: -22, max: 22, unit: '%' },
        dp: { min: -28, max: 28, unit: '%' },
        fixation: { min: 60, max: 100, unit: '%' }
    }
};

// Helper to check if value is within normal range
export function isNormal(value: number, range: { min: number; max: number }): boolean {
    return value >= range.min && value <= range.max;
}

// Helper to format value with unit
export function formatValue(value: number, unit: string, decimals = 1): string {
    return `${value.toFixed(decimals)}${unit ? ` ${unit}` : ''}`;
}
