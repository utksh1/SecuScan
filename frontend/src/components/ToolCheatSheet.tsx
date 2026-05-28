import React, { useState } from 'react';
import { learningData } from '../data/learningContent';

interface ToolCheatSheetProps {
  activeTool: string;
}

export default function ToolCheatSheet({ activeTool }: ToolCheatSheetProps) {
  const [isOpen, setIsOpen] = useState(true);

  const normalizedKey = activeTool ? activeTool.toLowerCase() : '';
  const currentData = learningData[normalizedKey];

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed right-0 top-1/3 bg-[#238636] hover:bg-[#2ea043] text-white px-2 py-4 rounded-l-md shadow-lg transition-all duration-200 z-50 flex flex-col items-center gap-1 font-medium text-xs [writing-mode:vertical-lr]"
        title="Open Learning Guide"
      >
        💡 <span className="tracking-wider mt-1">LEARN</span>
      </button>
    );
  }

  return (
    <aside className="w-80 h-full bg-[#161b22] border-l border-[#30363d] flex flex-col transition-all duration-300 shadow-2xl overflow-y-auto">
      {/* Header */}
      <div className="p-4 border-b border-[#30363d] flex justify-between items-center bg-[#0d1117]">
        <div className="flex items-center gap-2">
          <span className="text-lg">💡</span>
          <h3 className="font-semibold text-gray-100 text-xs tracking-wide uppercase">
            Learning Center
          </h3>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="text-gray-400 hover:text-gray-200 p-1 rounded hover:bg-[#21262d] text-xs transition"
        >
          ✕ Hide
        </button>
      </div>

      {/* Content */}
      <div className="p-4 flex-1 flex flex-col gap-4">
        {currentData ? (
          <>
            <div>
              <h4 className="text-[#58a6ff] text-sm font-medium mb-1">
                {currentData.title}
              </h4>
              <p className="text-gray-300 text-xs leading-relaxed">
                {currentData.overview}
              </p>
            </div>

            <div>
              <h5 className="text-gray-400 font-medium text-[10px] tracking-wider uppercase mb-2">
                Common Flags
              </h5>
              <div className="flex flex-col gap-2">
                {currentData.flags.map((item, index) => (
                  <div key={index} className="bg-[#0d1117] p-2 rounded border border-[#21262d]">
                    <code className="text-[#7ee787] text-xs font-mono font-semibold bg-[#21262d] px-1 py-0.5 rounded border border-[#30363d] inline-block mb-1">
                      {item.flag}
                    </code>
                    <p className="text-gray-400 text-xs">
                      {item.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-auto bg-[#382324] border border-[#f85149]/30 text-[#f85149] p-3 rounded-md text-xs leading-relaxed">
              <div className="font-bold mb-1 uppercase tracking-wide flex items-center gap-1">
                <span>⚠️</span> Ethical Note
              </div>
              <p className="text-gray-200">{currentData.ethical_tip}</p>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center text-center h-48 text-gray-500 text-xs">
            <span>🔍</span>
            <p className="mt-1">Select a tool tab to view information.</p>
          </div>
        )}
      </div>
    </aside>
  );
}