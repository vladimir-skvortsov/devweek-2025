import TokenizedText from './TokenizedText';

export default function TextInput({
  text,
  tokens,
  loading,
  onTextChange,
  onClearText,
  onFileUpload,
  onTokenClick,
  onAnalyze,
}) {
  return (
    <div className='relative'>
      {tokens.length > 0 ? (
        <TokenizedText text={text} tokens={tokens} onTokenClick={onTokenClick} />
      ) : (
        <textarea
          className='w-full min-h-56 h-56 max-h-96 overflow-y-auto p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#4F46E5] focus:border-[#4F46E5]'
          placeholder='Введите текст для анализа...'
          value={text}
          onChange={onTextChange}
          maxLength={10000}
        />
      )}
      <div className='flex justify-between items-center mt-1'>
        <div className='text-sm text-gray-500'>{text.length} / 10000 символов</div>
        <button
          onClick={onClearText}
          disabled={!text.trim()}
          className={`text-sm px-3 py-1 rounded transition-colors
            ${
              !text.trim() ? 'text-gray-400 cursor-not-allowed' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
        >
          Очистить поле
        </button>
      </div>

      <div className='mt-6 flex justify-center space-x-4'>
        <label
          className={`px-6 py-2 rounded-lg font-medium transition-colors relative group flex items-center space-x-2
          ${loading ? 'text-gray-400 cursor-not-allowed' : 'cursor-pointer text-gray-900 hover:bg-gray-100'}`}
        >
          <svg xmlns='http://www.w3.org/2000/svg' className='h-5 w-5' viewBox='0 0 20 20' fill='currentColor'>
            <path
              fillRule='evenodd'
              d='M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z'
              clipRule='evenodd'
            />
          </svg>
          <span>Загрузить файл</span>
          <div className='absolute top-full left-1/2 transform -translate-x-1/2 mt-2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none'>
            Поддерживаемые форматы:
            <br />
            .txt, .doc, .docs, .pdf, .pptx
            <br />
            .png, .jpg, .jpeg, .gif, .bmp
          </div>
          <input
            type='file'
            className='hidden'
            onChange={onFileUpload}
            accept='.txt,.doc,.docx,.pdf,.pptx,.png,.jpg,.jpeg,.gif,.bmp'
            disabled={loading}
          />
        </label>

        <button
          onClick={onAnalyze}
          disabled={loading || !text.trim()}
          className={`px-6 py-2 rounded-lg font-medium text-white transition-colors
            ${loading || !text.trim() ? 'bg-gray-400 cursor-not-allowed' : 'bg-[#4F46E5] hover:bg-[#6a63e9]'}`}
        >
          {loading ? 'Анализ...' : 'Анализировать текст'}
        </button>
      </div>
    </div>
  );
}
