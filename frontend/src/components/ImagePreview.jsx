

const ImagePreview = ({ maskedImage }) => {
  if (!maskedImage) return null;

  const downloadImage = () => {
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${maskedImage}`;
    link.download = 'masked_image.png';
    link.click();
  };

  return (
    <div className="relative w-full max-w-3xl mx-auto text-center mt-10 space-y-6">
      {/* Arrows appear alongside image */}

      <h2 className="text-3xl font-bold text-green-200 drop-shadow-[0_0_10px_rgba(0,255,145,0.6)]">
        ✅ Masked Image Preview
      </h2>

      <div className="rounded-xl border border-white/10 p-4 bg-white/5 backdrop-blur-md shadow-lg">
        <img
          src={`data:image/png;base64,${maskedImage}`}
          alt="Masked image preview"
          className="w-full max-h-[500px] object-contain rounded-md shadow-md"
        />
      </div>

      <button
        onClick={downloadImage}
        aria-label="Download masked image"
        className="mt-4 px-6 py-2 bg-gradient-to-r from-green-400 to-green-700 text-white font-semibold rounded-lg shadow-lg hover:from-green-300 hover:to-green-600 transition-all duration-300 border border-green-300 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-green-300"
      >
        ⬇️ Download Masked Image
      </button>
    </div>
  );
};

export default ImagePreview;
