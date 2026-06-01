import React, { useState } from 'react';
import { AlertTriangle, Check, Copy } from 'lucide-react';

interface CopyToClipboardProps {
  textToCopy: string;
}

const CopyToClipboard: React.FC<CopyToClipboardProps> = ({ textToCopy }) => {
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'error'>('idle');

  const handleCopy = async (): Promise<void> => {
    if (!textToCopy) return;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopyState('copied');
    } catch (err) {
      setCopyState('error');
      console.error('Failed to copy text: ', err);
    }
    setTimeout(() => setCopyState('idle'), 2000);
  };

  const buttonTone = {
    idle: 'bg-black/30 border-white/10 text-silver hover:bg-white/5 hover:text-white',
    copied: 'bg-green-900/30 border-green-500 text-green-400',
    error: 'bg-red-900/30 border-red-500 text-red-300',
  }[copyState];

  const buttonContent = {
    idle: { icon: <Copy size={12} aria-hidden="true" />, label: 'Copy Output' },
    copied: { icon: <Check size={12} aria-hidden="true" />, label: 'Copied!' },
    error: { icon: <AlertTriangle size={12} aria-hidden="true" />, label: 'Copy failed' },
  }[copyState];

  return (
    <button
      onClick={handleCopy}
      type="button"
      title="Copy to clipboard"
      className={`flex items-center gap-1.5 border px-3 py-2 text-[10px] uppercase tracking-[0.2em] font-medium transition-all duration-200 ${buttonTone}`}
    >
      {buttonContent.icon}
      <span aria-live="polite">{buttonContent.label}</span>
    </button>
  );
};

export default CopyToClipboard;
