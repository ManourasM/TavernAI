import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import useMenuStore from '../store/menuStore';
import MenuOCR from '../components/MenuOCR';
import MenuEditor from '../components/MenuEditor';
import './SetupPage.css';

function SetupPage() {
  const [step, setStep] = useState(1); // 1: capture, 2: OCR processing, 3: edit menu
  const [image, setImage] = useState(null);
  const [extractedMenu, setExtractedMenu] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const saveMenu = useMenuStore((state) => state.saveMenu);
  const navigate = useNavigate();

  const handleTakePhoto = async () => {
    try {
      const photo = await Camera.getPhoto({
        quality: 90,
        allowEditing: false,
        resultType: CameraResultType.DataUrl,
        source: CameraSource.Camera,
      });

      setImage(photo.dataUrl);
      setStep(2);
    } catch (error) {
      console.error('Error taking photo:', error);
      alert('Failed to take photo. Please try again.');
    }
  };

  const handleUploadPhoto = async () => {
    try {
      const photo = await Camera.getPhoto({
        quality: 90,
        allowEditing: false,
        resultType: CameraResultType.DataUrl,
        source: CameraSource.Photos,
      });

      setImage(photo.dataUrl);
      setStep(2);
    } catch (error) {
      console.error('Error uploading photo:', error);
      alert('Failed to upload photo. Please try again.');
    }
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
            onBack={() => setStep(2)}
            loading={loading}
          />
        )}
      </div>
    </div>
  );
}

export default SetupPage;

