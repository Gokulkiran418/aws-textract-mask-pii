import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import MetaBalls from './reactbits/MetaBalls';
import { motion } from 'framer-motion';

const NeonRingLoader = () => (
  <div className="relative w-24 h-24 flex items-center justify-center">
    <motion.div
      className="absolute w-24 h-24 rounded-full border-4 border-green-400"
      animate={{ scale: [1, 1.5], opacity: [1, 0] }}
      transition={{
        repeat: Infinity,
        repeatType: 'loop',
        duration: 1.2,
        ease: 'easeOut',
      }}
    />
    <motion.div
      className="absolute w-16 h-16 rounded-full border-4 border-green-300"
      animate={{ scale: [1, 1.3], opacity: [1, 0.5] }}
      transition={{
        repeat: Infinity,
        repeatType: 'loop',
        duration: 1,
        ease: 'easeInOut',
      }}
    />
    <div className="relative w-4 h-4 rounded-full bg-green-200" />
  </div>
);

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
    <div className="uploader w-full max-w-3xl mx-auto text-center text-white">
      {/* Dropzone with MetaBalls */}
      <div className="relative h-[400px] w-full overflow-hidden flex items-center justify-center">
        {/* MetaBalls background – centered and visible */}
        <div className="absolute inset-0 z-0 flex items-center justify-center">
          <MetaBalls
            color="#00ff91ff"
            cursorBallColor="#000000ff"
            cursorBallSize={3}
            ballCount={20}
            animationSize={25}
            enableMouseInteraction={true}
            enableTransparency={true}
            hoverSmoothness={0.04}
            clumpFactor={1.2}
            speed={0.5}
          />
        </div>

        {/* Conditional dropzone or loader */}
        <div className="relative z-10 flex flex-col items-center justify-center">
          {!loading ? (
            <div
              {...getRootProps()}
              className="w-[350px] h-[350px] border-4 border-white/20 rounded-full flex items-center justify-center cursor-pointer transition hover:scale-105 hover:border-green-400"
              aria-label="Drag and drop image or click to upload"
            >
              <input {...getInputProps()} />
              {isDragActive ? (
                <p className="text-pink-400 text-lg font-semibold text-center">
                  Drop it like it’s hot 🔥
                </p>
              ) : (
                <p className="text-white text-lg font-medium text-center">
                  Drag & Drop <br />or <span className="underline">Click</span> to Upload<br />
                  <span className="text-sm text-white/60">(PNG / JPEG)</span>
                </p>
              )}
            </div>
          ) : (
            <NeonRingLoader />
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <p className="mt-4 text-red-400 font-semibold" aria-live="assertive">
          ❌ {error}
        </p>
      )}
    </div>
  );
};

export default ImageUploader;
