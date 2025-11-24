import { useState, useEffect } from 'react';
import { createWorker } from 'tesseract.js';
import './MenuOCR.css';

function MenuOCR({ image, onComplete, onBack }) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('Initializing OCR...');
  const [extractedText, setExtractedText] = useState('');
  const [processing, setProcessing] = useState(true);

  useEffect(() => {
    performOCR();
  }, [image]);

  const performOCR = async () => {
    try {
      setStatus('Loading OCR engine...');
      const worker = await createWorker('ell', 1, {
        logger: (m) => {
          if (m.status === 'recognizing text') {
            setProgress(Math.round(m.progress * 100));
            setStatus(`Recognizing text... ${Math.round(m.progress * 100)}%`);
          }
        },
      });

      setStatus('Processing image...');
      const { data: { text } } = await worker.recognize(image);
      
      setExtractedText(text);
      setStatus('Parsing menu items...');
      
      // Parse the extracted text into menu items
      const menuItems = parseMenuText(text);
      
      await worker.terminate();
      setProcessing(false);
      setStatus('Complete!');
      
      // Auto-advance after a short delay
      setTimeout(() => {
        onComplete(menuItems);
      }, 1000);
      
    } catch (error) {
      console.error('OCR Error:', error);
      setStatus('Error processing image');
      setProcessing(false);
    }
  };

  const parseMenuText = (text) => {
    const lines = text.split('\n').filter(line => line.trim());
    const menuItems = [];
    
    // Simple parsing logic - can be enhanced with AI
    lines.forEach((line, index) => {
      // Try to extract item name and price
      // Pattern: "Item name ... price€" or "Item name price"
      const priceMatch = line.match(/(\d+(?:[.,]\d{1,2})?)\s*€?$/);
      
      if (priceMatch) {
        const price = parseFloat(priceMatch[1].replace(',', '.'));
        const name = line.substring(0, priceMatch.index).trim();
        
        if (name && price) {
          menuItems.push({
            id: Date.now() + index,
            name: name,
            price: price,
            category: 'kitchen', // Default category
            unit: 'portion',
          });
        }
      }
    });
    
    return menuItems;
  };

  return (
    <div className="menu-ocr">
      <div className="ocr-header">
        <button onClick={onBack} className="back-button">← Back</button>
        <h2>Processing Menu</h2>
      </div>

      <div className="ocr-content">
        <div className="image-preview">
          <img src={image} alt="Menu" />
        </div>

        <div className="ocr-progress">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="status-text">{status}</p>
        </div>

        {extractedText && (
          <div className="extracted-text">
            <h3>Extracted Text:</h3>
            <pre>{extractedText}</pre>
          </div>
        )}

        {!processing && (
          <div className="ocr-actions">
            <button onClick={onBack} className="secondary-button">
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default MenuOCR;

