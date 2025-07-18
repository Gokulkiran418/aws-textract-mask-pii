import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';

const ImageUploader = ({ onImageProcessed }) => {
  const [maskType, setMaskType] = useState('rectangle');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const onDrop = useCallback(async (acceptedFiles) => {
    setLoading(true);
    setError(null);
    const file = acceptedFiles[0];
    if (!file || !['image/png', 'image/jpeg'].includes(file.type)) {
      setError('Please upload a PNG or JPEG image.');
      setLoading(false);
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('mask_type', maskType);

    try {
      const response = await axios.post('http://localhost:8000/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      onImageProcessed(response.data.masked_image);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to process image.');
    } finally {
      setLoading(false);
    }
  }, [maskType, onImageProcessed]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, maxFiles: 1 });

  return (
    <div className="uploader">
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'active' : ''}`}
        aria-label="Drag and drop image or click to upload"
      >
        <input {...getInputProps()} />
        {isDragActive ? (
          <p>Drop the image here...</p>
        ) : (
          <p>Drag & drop an image, or click to select (PNG/JPEG)</p>
        )}
      </div>
      <div className="mask-type-selector">
        <label htmlFor="mask-type">Masking Style:</label>
        <select
          id="mask-type"
          value={maskType}
          onChange={(e) => setMaskType(e.target.value)}
          aria-label="Select masking style"
        >
          <option value="rectangle">Rectangle</option>
          <option value="blur">Blur</option>
        </select>
      </div>
      {loading && <p aria-live="polite">Processing image...</p>}
      {error && <p className="error" aria-live="assertive">{error}</p>}
    </div>
  );
};

export default ImageUploader;