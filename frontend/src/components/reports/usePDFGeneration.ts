import { useState, useCallback } from 'react';
import { save } from '@tauri-apps/plugin-dialog';
import { writeFile } from '@tauri-apps/plugin-fs';

export interface PDFGenerationOptions {
    filename?: string;
    quality?: number;
    scale?: number;
    margin?: number;
}

export interface PDFGenerationResult {
    success: boolean;
    error?: string;
}

/**
 * Capture computed RGB colors from all elements inside a root,
 * keyed by a data attribute we stamp on each element.
 * Must be called BEFORE neutralizing oklch so values are correct.
 */
function captureComputedColors(root: HTMLElement): Map<string, { color: string; bg: string; border: string }> {
    const map = new Map<string, { color: string; bg: string; border: string }>();
    const els = root.querySelectorAll('*');
    els.forEach((el, i) => {
        const htmlEl = el as HTMLElement;
        const key = `__pdf_${i}`;
        htmlEl.dataset.pdfKey = key;
        const cs = getComputedStyle(htmlEl);
        map.set(key, {
            color: cs.color,
            bg: cs.backgroundColor,
            border: cs.borderColor,
        });
    });
    return map;
}

/**
 * Temporarily neutralize oklch() in all stylesheets so html2canvas can parse them.
 * Returns a restore function.
 */
function neutralizeOklch(): () => void {
    const savedStyles: { el: HTMLStyleElement; original: string }[] = [];
    const disabledLinks: HTMLLinkElement[] = [];

    document.querySelectorAll('style').forEach((styleEl) => {
        const text = styleEl.textContent || '';
        if (text.includes('oklch')) {
            savedStyles.push({ el: styleEl as HTMLStyleElement, original: text });
            styleEl.textContent = text.replace(/oklch\([^)]*\)/g, 'transparent');
        }
    });

    document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]').forEach((linkEl) => {
        try {
            const sheet = linkEl.sheet;
            if (!sheet) return;
            let hasOklch = false;
            for (let i = 0; i < sheet.cssRules.length; i++) {
                if (sheet.cssRules[i].cssText.includes('oklch')) {
                    hasOklch = true;
                    break;
                }
            }
            if (hasOklch) {
                linkEl.disabled = true;
                disabledLinks.push(linkEl);
                const sanitized = document.createElement('style');
                sanitized.dataset.pdfFallback = 'true';
                let css = '';
                for (let i = 0; i < sheet.cssRules.length; i++) {
                    css += sheet.cssRules[i].cssText.replace(/oklch\([^)]*\)/g, 'transparent') + '\n';
                }
                sanitized.textContent = css;
                document.head.appendChild(sanitized);
            }
        } catch { /* CORS */ }
    });

    return () => {
        savedStyles.forEach(({ el, original }) => { el.textContent = original; });
        disabledLinks.forEach((l) => { l.disabled = false; });
        document.querySelectorAll('style[data-pdf-fallback]').forEach((el) => el.remove());
    };
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

        let restoreStyles: (() => void) | null = null;

        try {
            const [jsPDFModule, html2canvasModule] = await Promise.all([
                import('jspdf'),
                import('html2canvas')
            ]);

            const jsPDF = jsPDFModule.default;
            const html2canvas = html2canvasModule.default;

            setProgress(20);

            // 1. Capture correct RGB colors BEFORE neutralizing
            const colorMap = captureComputedColors(element);

            // 2. Neutralize oklch so html2canvas parser doesn't crash
            restoreStyles = neutralizeOklch();

            // 3. Render — use onclone to restore correct colors via inline styles
            const canvas = await html2canvas(element, {
                scale,
                useCORS: true,
                logging: false,
                backgroundColor: '#ffffff',
                onclone: (_doc: Document, clonedEl: HTMLElement) => {
                    // Apply saved RGB colors to cloned elements
                    clonedEl.querySelectorAll('[data-pdf-key]').forEach((el) => {
                        const htmlEl = el as HTMLElement;
                        const key = htmlEl.dataset.pdfKey!;
                        const saved = colorMap.get(key);
                        if (saved) {
                            htmlEl.style.color = saved.color;
                            htmlEl.style.backgroundColor = saved.bg;
                            htmlEl.style.borderColor = saved.border;
                        }
                    });
                },
            });

            // 4. Restore stylesheets immediately
            restoreStyles();
            restoreStyles = null;

            // Clean up data attributes
            element.querySelectorAll('[data-pdf-key]').forEach((el) => {
                (el as HTMLElement).removeAttribute('data-pdf-key');
            });

            setProgress(60);

            const imgWidth = 210 - (margin * 2);
            const pageHeight = 297 - (margin * 2);
            const imgHeight = (canvas.height * imgWidth) / canvas.width;
            const imgData = canvas.toDataURL('image/jpeg', quality);

            setProgress(80);

            const pdf = new jsPDF('p', 'mm', 'a4');
            let heightLeft = imgHeight;
            let position = margin;

            pdf.addImage(imgData, 'JPEG', margin, position, imgWidth, imgHeight);
            heightLeft -= pageHeight;

            while (heightLeft > 0) {
                position = heightLeft - imgHeight + margin;
                pdf.addPage();
                pdf.addImage(imgData, 'JPEG', margin, position, imgWidth, imgHeight);
                heightLeft -= pageHeight;
            }

            setProgress(100);

            const pdfBytes = pdf.output('arraybuffer');

            const savePath = await save({
                defaultPath: filename,
                filters: [{ name: 'PDF', extensions: ['pdf'] }],
            });

            if (!savePath) {
                return { success: false };
            }

            await writeFile(savePath, new Uint8Array(pdfBytes));

            return { success: true };

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Error generating PDF';

            if (errorMessage.includes('Cannot find module') || errorMessage.includes('Failed to resolve')) {
                return {
                    success: false,
                    error: 'PDF dependencies not installed. Run: npm install jspdf html2canvas'
                };
            }

            return { success: false, error: errorMessage };
        } finally {
            if (restoreStyles) restoreStyles();
            // Clean up data attributes on error too
            element.querySelectorAll('[data-pdf-key]').forEach((el) => {
                (el as HTMLElement).removeAttribute('data-pdf-key');
            });
            setIsGenerating(false);
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

    const printReport = useCallback((reportContainer: HTMLElement) => {
        // Mark the report container so CSS can target it
        reportContainer.dataset.printing = 'true';

        // Inject print-specific CSS
        const printStyle = document.createElement('style');
        printStyle.dataset.printHelper = 'true';
        printStyle.textContent = `
            @media print {
                /* Hide everything */
                body > * { display: none !important; }
                /* Show only the app root, then drill down to the report */
                #root, #root > *, #root > * > * { display: block !important; }

                /* Hide all app chrome */
                [data-printing="true"] {
                    display: block !important;
                    position: fixed !important;
                    inset: 0 !important;
                    z-index: 99999 !important;
                    background: white !important;
                    overflow: visible !important;
                    max-width: none !important;
                    width: 100% !important;
                    padding: 0 !important;
                    margin: 0 !important;
                    box-shadow: none !important;
                    min-height: auto !important;
                }

                /* Ensure ancestors are visible */
                [data-printing="true"],
                [data-printing="true"] * {
                    color-adjust: exact !important;
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }

                /* Hide editing controls */
                .report-controls { display: none !important; }

                @page { size: A4; margin: 10mm; }
            }
        `;
        document.head.appendChild(printStyle);

        // Use a small delay to let the style apply
        requestAnimationFrame(() => {
            window.print();

            // Cleanup after print dialog closes
            delete reportContainer.dataset.printing;
            printStyle.remove();
        });
    }, []);

    return {
        generatePDF,
        generateFromSections,
        printReport,
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

export function isNormal(value: number, range: { min: number; max: number }): boolean {
    return value >= range.min && value <= range.max;
}

export function formatValue(value: number, unit: string, decimals = 1): string {
    return `${value.toFixed(decimals)}${unit ? ` ${unit}` : ''}`;
}
