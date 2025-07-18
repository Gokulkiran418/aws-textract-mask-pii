import React from 'react';

const ImagePreview = ({ maskedImage }) => {
  if (!maskedImage) return null;

  const downloadImage = () => {
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${maskedImage}`;
    link.download = 'masked_image.png';
    link.click();
  };

  return (
    <div className="preview">
      <h2>Masked Image Preview</h2>
      <img
        src={`data:image/png;base64,${maskedImage}`}
        alt="Masked image preview"
        style={{ maxWidth: '100%', height: 'auto' }}
      />
      <button onClick={downloadImage} aria-label="Download masked image">
        Download Masked Image
      </button>
    </div>
  );
};

export default ImagePreview;