import { useMemo } from 'react';

export default function TokenInfo({ token }) {
  const tokenInfo = useMemo(() => {
    if (!token) return null;

    return {
      type: token.type,
      typeText: token.type === 'word' ? 'Слово' : 'Знак препинания',
      typeColor: token.type === 'word' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800',
      examples: token.examples || [],
      recommendations: token.recommendations || [],
    };
  }, [token]);

  if (!token) {
    return null;
  }

  return (
    <div className='mt-4 p-4 bg-white rounded-lg shadow-sm border border-gray-200'>
      <div className='flex items-center justify-between mb-4'>
        <div className='flex items-center space-x-2'>
          <span className='text-lg font-medium'>{token.text}</span>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${tokenInfo.typeColor}`}>
            {tokenInfo.typeText}
          </span>
        </div>
      </div>

      {tokenInfo.examples.length > 0 && (
        <div className='mb-4'>
          <h4 className='text-sm font-medium text-gray-700 mb-2'>Примеры использования:</h4>
          <ul className='list-disc list-inside space-y-1 text-sm text-gray-600'>
            {tokenInfo.examples.map((example, index) => (
              <li key={index}>{example}</li>
            ))}
          </ul>
        </div>
      )}

      {tokenInfo.recommendations.length > 0 && (
        <div>
          <h4 className='text-sm font-medium text-gray-700 mb-2'>Рекомендации:</h4>
          <ul className='list-disc list-inside space-y-1 text-sm text-gray-600'>
            {tokenInfo.recommendations.map((rec, index) => (
              <li key={index}>{rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
