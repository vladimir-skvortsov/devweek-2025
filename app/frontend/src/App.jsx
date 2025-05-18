import { useState } from 'react';

function App() {
  const [text, setText] = useState('');
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyzeText = async () => {
    if (!text.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/v1/score', {
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
    } catch (err) {
      setError('Failed to analyze text. Please try again.');
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
    if (score === null) return 'Not analyzed';
    if (score < 0.3) return 'Likely AI-generated';
    if (score < 0.7) return 'Uncertain';
    return 'Likely Human-written';
  };

  return (
    <div className='min-h-screen bg-gray-100 py-12 px-4 sm:px-6 lg:px-8'>
      <div className='max-w-3xl mx-auto'>
        <div className='text-center mb-8'>
          <h1 className='text-3xl font-bold text-gray-900 mb-2'>AI Text Detector</h1>
          <p className='text-gray-600'>Enter text to analyze if it was written by AI or a human</p>
        </div>

        <div className='bg-white rounded-lg shadow-lg p-6'>
          <textarea
            className='w-full h-48 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none'
            placeholder='Enter text to analyze...'
            value={text}
            onChange={(e) => setText(e.target.value)}
          />

          <div className='mt-4 flex justify-center'>
            <button
              onClick={analyzeText}
              disabled={loading || !text.trim()}
              className={`px-6 py-2 rounded-lg font-medium text-white transition-colors
                ${loading || !text.trim() ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
            >
              {loading ? 'Analyzing...' : 'Analyze Text'}
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
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
