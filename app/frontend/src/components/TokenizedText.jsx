import { useState, useMemo } from 'react';

const TokenizedText = ({ text, tokens, onTokenClick }) => {
  const [hoveredToken, setHoveredToken] = useState(null);

  // Function to get color based on AI probability
  const getTokenColor = (aiProb) => {
    return `rgb(79, 70, 229, ${aiProb / 2})`;
  };

  // Function to get text color based on background
  const getTextColor = (aiProb) => {
    return aiProb > 0.5 ? 'text-gray-900' : 'text-gray-800';
  };

  // Function to get tooltip text
  const getTooltipText = (token, aiProb) => {
    const percentage = (aiProb * 100).toFixed(1);
    return `${token}: ${percentage}% вероятность написания ИИ`;
  };

  // Find token positions in the original text
  const tokenPositions = useMemo(() => {
    const positions = [];
    let currentIndex = 0;

    tokens.forEach((token, tokenIndex) => {
      // Skip special tokens
      if (token.is_special_token) return;

      // Find the token in the text starting from the current position
      const tokenText = token.token.replace('##', ''); // Remove BERT token prefixes
      const startIndex = text.toLowerCase().indexOf(tokenText.toLowerCase(), currentIndex);

      if (startIndex !== -1) {
        positions.push({
          start: startIndex,
          end: startIndex + tokenText.length,
          tokenIndex,
          token,
        });
        currentIndex = startIndex + tokenText.length;
      }
    });

    return positions;
  }, [text, tokens]);

  // Split text into highlighted and non-highlighted parts
  const textParts = useMemo(() => {
    if (tokenPositions.length === 0) return [{ text, isToken: false }];

    const parts = [];
    let lastIndex = 0;

    tokenPositions.forEach(({ start, end, tokenIndex, token }) => {
      // Add non-token text before this token
      if (start > lastIndex) {
        parts.push({
          text: text.slice(lastIndex, start),
          isToken: false,
        });
      }

      // Add the token
      parts.push({
        text: text.slice(start, end),
        isToken: true,
        tokenIndex,
        token,
      });

      lastIndex = end;
    });

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push({
        text: text.slice(lastIndex),
        isToken: false,
      });
    }

    return parts;
  }, [text, tokenPositions]);

  return (
    <div className='relative w-full min-h-56 h-56 max-h-96 overflow-y-auto p-4 border border-gray-300 rounded-lg bg-white'>
      <div className='whitespace-pre-wrap break-words'>
        {textParts.map((part, index) => {
          if (!part.isToken) {
            return <span key={index}>{part.text}</span>;
          }

          const { token, tokenIndex } = part;
          return (
            <span
              key={index}
              className={`inline-block px-0.5 py-0.5 cursor-pointer transition-all duration-200 ${
                hoveredToken === tokenIndex ? 'ring-2 ring-[#4F46E5]' : ''
              }`}
              style={{
                backgroundColor: getTokenColor(token.ai_prob),
              }}
              onMouseEnter={() => setHoveredToken(tokenIndex)}
              onMouseLeave={() => setHoveredToken(null)}
              onClick={() => onTokenClick(token)}
              title={getTooltipText(token.token, token.ai_prob)}
            >
              <span className={getTextColor(token.ai_prob)}>{part.text}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
};

export default TokenizedText;
