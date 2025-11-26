import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import useMenuStore from '../store/menuStore';
import MenuOCR from '../components/MenuOCR';
import MenuEditor from '../components/MenuEditor';
import './SetupPage.css';

function SetupPage() {
  const [step, setStep] = useState(1); // 1: capture, 2: OCR processing, 3: edit menu
  const [image, setImage] = useState(null);
  const [extractedMenu, setExtractedMenu] = useState(null);
  const [loading, setLoading] = useState(false);

  const cameraInputRef = useRef(null);
  const fileInputRef = useRef(null);

  const saveMenu = useMenuStore((state) => state.saveMenu);
  const navigate = useNavigate();

  const handleTakePhoto = () => {
    // Trigger camera input
    if (cameraInputRef.current) {
      cameraInputRef.current.click();
    }
  };

  const handleUploadPhoto = () => {
    // Trigger file input
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Check if it's an image
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file');
      return;
    }

    // Convert to data URL
    const reader = new FileReader();
    reader.onload = (e) => {
      setImage(e.target.result);
      setStep(2);
    };
    reader.onerror = () => {
      alert('Failed to read file. Please try again.');
    };
    reader.readAsDataURL(file);
  };

  const handleOCRComplete = (menu) => {
    setExtractedMenu(menu);
    setStep(3);
  };

  const handleSaveMenu = async (finalMenu) => {
    setLoading(true);
    const result = await saveMenu(finalMenu);
    
    if (result.success) {
      navigate('/home');
    } else {
      alert('Failed to save menu. Please try again.');
    }
    
    setLoading(false);
  };

  const handleSkipSetup = () => {
    // Use default menu or empty menu
    navigate('/home');
  };

  return (
    <div className="setup-page">
      <div className="setup-container">
        <div className="setup-header">
          <h1>📋 Menu Setup</h1>
          <p>Let's set up your menu</p>
        </div>

        {step === 1 && (
          <div className="setup-step">
            <h2>Step 1: Capture Menu</h2>
            <p>Take a photo of your menu or upload an existing image</p>

            {/* Hidden file inputs */}
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />

            <div className="button-group">
              <button onClick={handleTakePhoto} className="primary-button">
                📷 Take Photo
              </button>
              <button onClick={handleUploadPhoto} className="secondary-button">
                📁 Upload Image
              </button>
            </div>

            <div className="skip-section">
              <button onClick={handleSkipSetup} className="text-button">
                Skip setup (use default menu)
              </button>
            </div>
          </div>
        )}

        {step === 2 && image && (
          <MenuOCR
            image={image}
            onComplete={handleOCRComplete}
            onBack={() => {
              setImage(null);
              setStep(1);
            }}
          />
        )}

        {step === 3 && extractedMenu && (
          <MenuEditor
            initialMenu={extractedMenu}
            onSave={handleSaveMenu}
            onBack={() => {
              setImage(null);
              setExtractedMenu(null);
              setStep(1);
            }}
            loading={loading}
          />
        )}
      </div>
    </div>
  );
}

export default SetupPage;

