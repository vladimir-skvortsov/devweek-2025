import ShareLink from './ShareLink';

export default function AnalysisResult({ score, explanation, examples, tokens, shareLink, shareLoading, onShare }) {
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

  if (score === null) return null;

  return (
    <div className='mt-6'>
      <div className='flex items-center justify-center space-x-4'>
        <div className={`w-24 h-24 rounded-full ${getScoreColor(score)} flex items-center justify-center`}>
          <span className='text-white text-2xl font-bold'>{(score * 100).toFixed(1)}%</span>
        </div>
        <div className='text-lg font-medium text-gray-700'>{getScoreText(score)}</div>
      </div>

      <ShareLink shareLink={shareLink} shareLoading={shareLoading} onShare={onShare} disabled={!tokens.length} />

      <div className='mt-6 bg-white p-6 rounded-lg shadow-lg'>
        <h2 className='text-xl font-semibold mb-4'>Анализ текста</h2>
        <p className='text-gray-800 whitespace-pre-line'>{explanation}</p>
      </div>
      <div className='mt-6 bg-white p-6 rounded-lg shadow-lg'>
        <h2 className='text-xl font-semibold mb-4'>Рекомендации</h2>
        <p className='text-gray-800 whitespace-pre-line'>{examples}</p>
      </div>
    </div>
  );
}
