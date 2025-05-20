import { useState, useMemo } from 'react';

const SUSPICIOUS_THRESHOLD = 0.6;

const TokenizedText = ({ text, tokens, onTokenClick }) => {
  const [hoveredToken, setHoveredToken] = useState(null);

  const getTokenColor = (aiProb) => {
    if (aiProb < SUSPICIOUS_THRESHOLD) return 'transparent';
    const intensity = (aiProb - SUSPICIOUS_THRESHOLD) / (1 - SUSPICIOUS_THRESHOLD);
    return `rgba(79, 70, 229, ${0.1 + intensity * 0.5})`;
  };

  // Function to get text color based on background
  const getTextColor = (aiProb) => {
    return aiProb >= SUSPICIOUS_THRESHOLD ? 'text-gray-900' : 'text-gray-800';
  };

  // Function to get tooltip text
  const getTooltipText = (token, aiProb) => {
    if (aiProb < SUSPICIOUS_THRESHOLD) return null;
    const percentage = (aiProb * 100).toFixed(1);
    return `${token}: ${percentage}% вероятность написания ИИ`;
  };

  // Find token positions in the original text
  const tokenPositions = useMemo(() => {
    const positions = [];
    let currentIndex = 0;

    tokens.forEach((token, tokenIndex) => {
      // Skip special tokens and non-suspicious tokens
      if (token.is_special_token || token.ai_prob < SUSPICIOUS_THRESHOLD) return;

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
          const tooltipText = getTooltipText(token.token, token.ai_prob);

          return (
            <span
              key={index}
              className={`inline-block px-0.5 py-0.5 cursor-pointer ${
                hoveredToken === tokenIndex ? 'ring-2 ring-[#4F46E5]' : ''
              }`}
              style={{
                backgroundColor: getTokenColor(token.ai_prob),
              }}
              onMouseEnter={() => setHoveredToken(tokenIndex)}
              onMouseLeave={() => setHoveredToken(null)}
              onClick={() => onTokenClick(token)}
              title={tooltipText || undefined}
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
