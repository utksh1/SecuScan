import React from 'react'

export default function ConsentModal({ plugin, onConfirm, onCancel }) {
  if (!plugin) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-bold mb-4">Consent Required</h2>
        
        <div className="mb-4">
          <p className="text-gray-700 mb-2">
            You are about to run the <strong>{plugin.name}</strong> plugin.
          </p>
          
          {plugin.safety && (
            <div className="mb-4">
              <h3 className="font-semibold mb-2">Safety Information:</h3>
              <ul className="list-disc list-inside text-sm text-gray-600">
                <li>Safety Level: {plugin.safety?.level || 'Unknown'}</li>
                {plugin.safety?.requires_consent && (
                  <li>This plugin requires explicit consent</li>
                )}
                {plugin.safety?.description && (
                  <li>{plugin.safety.description}</li>
                )}
              </ul>
            </div>
          )}

          {plugin.description && (
            <div className="mb-4">
              <h3 className="font-semibold mb-2">Description:</h3>
              <p className="text-sm text-gray-600">{plugin.description}</p>
            </div>
          )}
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
          <p className="text-sm text-yellow-800">
            <strong>Warning:</strong> This plugin will perform network scanning activities. 
            Only proceed if you have proper authorization to scan the target.
          </p>
        </div>

        <div className="flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            I Understand, Proceed
          </button>
        </div>
      </div>
    </div>
  )
}
