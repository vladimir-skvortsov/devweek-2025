import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import Header from './components/Header';
import TextInput from './components/TextInput';
import TokenInfo from './components/TokenInfo';
import AnalysisResult from './components/AnalysisResult';

function App() {
  const [searchParams] = useSearchParams();
  const [text, setText] = useState('');
  const [score, setScore] = useState(null);
  const [explanation, setExplanation] = useState('');
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedToken, setSelectedToken] = useState(null);
  const [examples, setExamples] = useState('');
  const [shareLink, setShareLink] = useState('');
  const [shareLoading, setShareLoading] = useState(false);
  const [isSharedContent, setIsSharedContent] = useState(false);

  const fetchSharedData = useCallback(async (id) => {
    setLoading(true);
    setError(null);
    setIsSharedContent(true);
    try {
      const response = await fetch(`http://localhost:8000/api/v1/text/get?id=${id}`);
      if (!response.ok) {
        throw new Error('Failed to fetch shared data');
      }
      const data = await response.json();
      setText(data.text);
      setScore(data.score);
      setExplanation(data.explanation);
      setTokens(data.tokens);
      setExamples(data.examples);
    } catch (err) {
      setError('Failed to load shared data. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const sharedId = searchParams.get('id');
    if (sharedId) {
      fetchSharedData(sharedId);
    }
  }, [searchParams, fetchSharedData]);

  const handleShare = useCallback(async () => {
    if (!text.trim() || score === null) return;

    setShareLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/v1/text/share', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text,
          score,
          explanation,
          tokens,
          examples,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to share text');
      }

      const data = await response.json();
      const shareUrl = `${window.location.origin}${window.location.pathname}?id=${data.id}`;
      setShareLink(shareUrl);
    } catch (err) {
      setError('Failed to share text. Please try again.');
      console.error(err);
    } finally {
      setShareLoading(false);
    }
  }, [text, score, explanation, tokens, examples]);

  const analyzeText = useCallback(async () => {
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
      setExamples(data.examples);
    } catch (err) {
      setError('Failed to analyze text. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [text]);

  const handleFileUpload = useCallback(async (event) => {
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
      setExamples(data.examples);
    } catch (err) {
      setError('Failed to analyze file. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleTextChange = useCallback((e) => {
    const newText = e.target.value.slice(0, 10000);
    setText(newText);
    setScore(null);
    setTokens([]);
    setExplanation('');
    setExamples('');
    setError(null);
    setSelectedToken(null);
    setIsSharedContent(false);
  }, []);

  const handleClearText = useCallback(() => {
    setText('');
    setScore(null);
    setTokens([]);
    setExplanation('');
    setExamples('');
    setError(null);
    setSelectedToken(null);
    setIsSharedContent(false);
  }, []);

  const handleTokenClick = useCallback((token) => {
    setSelectedToken(token);
  }, []);

  const textInputProps = useMemo(
    () => ({
      text,
      tokens,
      loading,
      onTextChange: handleTextChange,
      onClearText: handleClearText,
      onFileUpload: handleFileUpload,
      onTokenClick: handleTokenClick,
      onAnalyze: analyzeText,
    }),
    [text, tokens, loading, handleTextChange, handleClearText, handleFileUpload, handleTokenClick, analyzeText]
  );

  const analysisResultProps = useMemo(
    () => ({
      score,
      explanation,
      examples,
      tokens,
      shareLink,
      shareLoading,
      onShare: handleShare,
      isSharedContent,
    }),
    [score, explanation, examples, tokens, shareLink, shareLoading, handleShare, isSharedContent]
  );

  return (
    <div className='min-h-screen bg-gray-100 py-12 px-4 sm:px-6 lg:px-8'>
      <div className='max-w-3xl mx-auto'>
        <Header />

        <div className='bg-white rounded-xl shadow-lg p-6'>
          <TextInput {...textInputProps} />

          <TokenInfo selectedToken={selectedToken} />

          {error && <div className='mt-4 text-red-600 text-center'>{error}</div>}

          <AnalysisResult {...analysisResultProps} />
        </div>
      </div>
    </div>
  );
}

export default App;
