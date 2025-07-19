import React, { useState } from 'react';
import ImageUploader from './components/ImageUploader';
import ImagePreview from './components/ImagePreview';
import ClickSpark from './components/reactbits/ClickSpark';
import Aurora from './components/reactbits/Aurora'; // Adjust path if needed

function App() {
  const [maskedImage, setMaskedImage] = useState(null);

  const handleImageProcessed = (maskedImage) => {
    setMaskedImage(maskedImage);
  };

 return (
  <ClickSpark
    sparkColor="#00ff95ff"
    sparkSize={27}
    sparkRadius={45}
    sparkCount={3}
    duration={700}
  >
    <div className="relative min-h-screen w-full overflow-hidden">
      {/* Aurora Background */}
      <Aurora
        colorStops={["#000000", "#00FFEA", "#000000", "#000000"]}
        blend={0.6}
        amplitude={1.2}
        speed={0.6}
        className="absolute inset-0 -z-20"
      />

      {/* Black base background to preserve ClickSpark visibility */}
      <div className="absolute inset-0 bg-black z-[-10]" />

      {/* Main Content */}
      <div className="relative z-10 flex flex-col items-center px-4 pt-4 pb-8">
        <h1 className="text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-green-200 via-green-400 to-green-800 drop-shadow-[0_2px_10px_rgba(255,255,255,0.25)] mb-10 text-center">
          PII Masking Application
        </h1>
        <ImageUploader onImageProcessed={handleImageProcessed} />
        <ImagePreview maskedImage={maskedImage} />
      </div>
    </div>
  </ClickSpark>
);

}

export default App;
