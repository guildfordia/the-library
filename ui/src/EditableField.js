/**
 * Inline editable field component for The Library
 * Allows clicking to edit any field with automatic save
 */
import React, { useState } from 'react';

const API_URL = process.env.REACT_APP_API_URL || '/api';

export const EditableField = ({
  entityType,  // 'book' or 'quote'
  entityId,
  fieldName,
  value,
  onSave,
  multiline = false,
  className = ""
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value || '');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleEdit = () => {
    setIsEditing(true);
    setEditValue(value || '');
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditValue(value || '');
    setError(null);
  };

  const handleSave = async () => {
    if (editValue === value) {
      setIsEditing(false);
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const endpoint = entityType === 'book'
        ? `${API_URL}/edits/books/${entityId}`
        : `${API_URL}/edits/quotes/${entityId}`;

      const response = await fetch(endpoint, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          [fieldName]: editValue
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save');
      }

      const result = await response.json();

      // Notify parent component
      console.log('EditableField: About to call onSave', { fieldName, editValue, onSave: !!onSave });
      if (onSave) {
        console.log('EditableField: Calling onSave now');
        onSave(fieldName, editValue, result);
        console.log('EditableField: onSave called successfully');
      } else {
        console.log('EditableField: No onSave callback provided!');
      }

      setIsEditing(false);
    } catch (err) {
      setError(err.message);
      console.error('Save failed:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      handleCancel();
    } else if (e.key === 'Enter' && !multiline) {
      e.preventDefault();
      handleSave();
    }
  };

  if (isEditing) {
    return (
      <div className="relative">
        {multiline ? (
          <textarea
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full border-2 border-blue-400 p-2 rounded min-h-[100px] focus:outline-none focus:border-blue-600"
            autoFocus
            disabled={isSaving}
          />
        ) : (
          <input
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full border-2 border-blue-400 p-2 rounded focus:outline-none focus:border-blue-600"
            autoFocus
            disabled={isSaving}
          />
        )}
        <div className="flex gap-2 mt-2">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-3 py-1 bg-black text-white text-sm font-bold hover:bg-gray-800 disabled:bg-gray-400"
          >
            {isSaving ? 'SAVING...' : 'SAVE'}
          </button>
          <button
            onClick={handleCancel}
            disabled={isSaving}
            className="px-3 py-1 border-2 border-gray-300 text-sm font-bold hover:border-black disabled:border-gray-400 disabled:text-gray-400"
          >
            CANCEL
          </button>
        </div>
        {error && (
          <div className="text-red-600 text-sm mt-1">
            Error: {error}
          </div>
        )}
        <div className="text-xs text-gray-500 mt-1">
          {multiline ? 'Ctrl+Enter to save, Esc to cancel' : 'Enter to save, Esc to cancel'}
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={handleEdit}
      className={`cursor-pointer hover:bg-yellow-50 transition-colors p-1 -m-1 rounded ${className}`}
      title="Click to edit"
    >
      {value || <span className="text-gray-400 italic">Click to add...</span>}
      <span className="ml-2 text-xs text-gray-400 opacity-0 group-hover:opacity-100">✎</span>
    </div>
  );
};

export default EditableField;
