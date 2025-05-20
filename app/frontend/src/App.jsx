import { useState } from 'react';
import TokenizedText from './components/TokenizedText';

function App() {
  const [text, setText] = useState('');
  const [score, setScore] = useState(null);
  const [explanation, setExplanation] = useState('');
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedToken, setSelectedToken] = useState(null);

  const analyzeText = async () => {
    if (!text.trim()) return;

    setLoading(true);
    setError(null);
    setSelectedToken(null);

    try {
      const response = await fetch('http://localhost:8000/api/v1/score/text', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        throw new Error('Failed to analyze text');
      }

      const data = await response.json();

      setScore(data.score);
      setExplanation(data.explanation);
      setTokens(data.tokens);
    } catch (err) {
      setError('Failed to analyze text. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    setSelectedToken(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/api/v1/score/file', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to analyze file');
      }

      const data = await response.json();
      setScore(data.score);
      setText(data.text);
      setExplanation(data.explanation);
      setTokens(data.tokens);
    } catch (err) {
      setError('Failed to analyze file. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score === null) return 'bg-gray-200';
    if (score < 0.3) return 'bg-red-500';
    if (score < 0.7) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getScoreText = (score) => {
    if (score === null) return 'Не проанализировано';
    if (score < 0.3) return 'Вероятно написано ИИ';
    if (score < 0.7) return 'Неопределенно';
    return 'Вероятно написано человеком';
  };

  const handleTextChange = (e) => {
    const newText = e.target.value.slice(0, 10000);
    setText(newText);
    setScore(null);
    setTokens([]);
    setExplanation('');
    setError(null);
    setSelectedToken(null);
  };

  const handleClearText = () => {
    setText('');
    setScore(null);
    setTokens([]);
    setExplanation('');
    setError(null);
    setSelectedToken(null);
  };

  const handleTokenClick = (token) => {
    setSelectedToken(token);
  };

  return (
    <div className='min-h-screen bg-gray-100 py-12 px-4 sm:px-6 lg:px-8'>
      <div className='max-w-3xl mx-auto'>
        <div className='text-center mb-8'>
          <h1 className='text-3xl font-bold text-gray-900 mb-2'>AI Text Detector</h1>
          <p className='text-gray-600'>
            Введите текст или загрузите файл, чтобы определить, написан ли он ИИ или человеком
          </p>
        </div>

        <div className='bg-white rounded-xl shadow-lg p-6'>
          <div className='relative'>
            {tokens.length > 0 ? (
              <TokenizedText text={text} tokens={tokens} onTokenClick={handleTokenClick} />
            ) : (
              <textarea
                className='w-full min-h-56 h-56 max-h-96 overflow-y-auto p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#4F46E5] focus:border-[#4F46E5]'
                placeholder='Введите текст для анализа...'
                value={text}
                onChange={handleTextChange}
                maxLength={10000}
              />
            )}
            <div className='flex justify-between items-center mt-1'>
              <div className='text-sm text-gray-500'>{text.length} / 10000 символов</div>
              <button
                onClick={handleClearText}
                disabled={!text.trim()}
                className={`text-sm px-3 py-1 rounded transition-colors
                  ${
                    !text.trim()
                      ? 'text-gray-400 cursor-not-allowed'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
              >
                Очистить поле
              </button>
            </div>
          </div>

          {selectedToken && (
            <div className='mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200'>
              <div className='text-sm text-gray-600'>
                <span className='font-medium'>Токен:</span> {selectedToken.token}
              </div>
              <div className='text-sm text-gray-600'>
                <span className='font-medium'>Вероятность ИИ:</span> {(selectedToken.ai_prob * 100).toFixed(1)}%
              </div>
            </div>
          )}

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
                onChange={handleFileUpload}
                accept='.txt,.doc,.docx,.pdf,.pptx,.png,.jpg,.jpeg,.gif,.bmp'
                disabled={loading}
              />
            </label>

            <button
              onClick={analyzeText}
              disabled={loading || !text.trim()}
              className={`px-6 py-2 rounded-lg font-medium text-white transition-colors
                ${loading || !text.trim() ? 'bg-gray-400 cursor-not-allowed' : 'bg-[#4F46E5] hover:bg-[#6a63e9]'}`}
            >
              {loading ? 'Анализ...' : 'Анализировать текст'}
            </button>
          </div>

          {error && <div className='mt-4 text-red-600 text-center'>{error}</div>}

          {score !== null && (
            <div className='mt-6'>
              <div className='flex items-center justify-center space-x-4'>
                <div className={`w-24 h-24 rounded-full ${getScoreColor(score)} flex items-center justify-center`}>
                  <span className='text-white text-2xl font-bold'>{(score * 100).toFixed(1)}%</span>
                </div>
                <div className='text-lg font-medium text-gray-700'>{getScoreText(score)}</div>
              </div>
              <div className='mt-6 bg-white p-6 rounded-lg shadow'>
                <h2 className='text-xl font-semibold mb-4'>Анализ текста</h2>
                <p className='text-gray-800 whitespace-pre-line'>{explanation}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
