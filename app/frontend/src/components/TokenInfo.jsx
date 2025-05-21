export default function TokenInfo({ selectedToken }) {
  if (!selectedToken) return null;

  return (
    <div className='mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200'>
      <div className='text-sm text-gray-600'>
        <span className='font-medium'>Токен:</span> {selectedToken.token}
      </div>
      <div className='text-sm text-gray-600'>
        <span className='font-medium'>Вероятность ИИ:</span> {(selectedToken.ai_prob * 100).toFixed(1)}%
      </div>
    </div>
  );
}
