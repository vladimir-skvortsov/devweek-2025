export default function ShareLink({ shareLink, shareLoading, onShare, disabled }) {
  if (shareLink) {
    return (
      <div className='mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200'>
        <div className='text-sm text-gray-600 mb-2'>Ссылка для просмотра:</div>
        <div className='flex items-center space-x-2'>
          <input
            type='text'
            value={shareLink}
            readOnly
            className='flex-1 p-2 border border-gray-300 rounded-lg bg-white text-sm'
          />
          <button
            onClick={() => {
              navigator.clipboard.writeText(shareLink);
            }}
            className='px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors'
          >
            Копировать
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className='mt-4 flex justify-center'>
      <button
        onClick={onShare}
        disabled={shareLoading || disabled}
        className={`px-4 py-2 rounded-lg font-medium text-white transition-colors flex items-center space-x-2
          ${shareLoading || disabled ? 'bg-gray-400 cursor-not-allowed' : 'bg-[#4F46E5] hover:bg-[#6a63e9]'}`}
      >
        <svg xmlns='http://www.w3.org/2000/svg' className='h-5 w-5' viewBox='0 0 20 20' fill='currentColor'>
          <path d='M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z' />
        </svg>
        <span>{shareLoading ? 'Поделиться...' : 'Поделиться анализом'}</span>
      </button>
    </div>
  );
}
