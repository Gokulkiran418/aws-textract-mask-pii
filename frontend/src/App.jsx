import React, { useState } from 'react';
import ImageUploader from './components/ImageUploader';
import ImagePreview from './components/ImagePreview';
import './styles/App.css';

function App() {
  const [maskedImage, setMaskedImage] = useState(null);

  const handleImageProcessed = (maskedImage) => {
    setMaskedImage(maskedImage);
  };

  return (
    <div className="app">
      <h1>PII Masking Application</h1>
      <ImageUploader onImageProcessed={handleImageProcessed} />
      <ImagePreview maskedImage={maskedImage} />
    </div>
  );
}

export default App;