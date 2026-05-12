import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Save } from 'lucide-react';
import locationService from '../../services/locationService';

export const WarehouseMapBuilder = ({ isOpen, onClose, onSuccess, defaultType = 'warehouse' }) => {
  const [blocks, setBlocks] = useState([
    { id: 1, name: '', rows: 6, cols: 3, columnGaps: [], type: defaultType }
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Reset blocks when modal opens or type changes
  useEffect(() => {
    if (isOpen) {
      setBlocks([{ id: Date.now(), name: '', rows: 6, cols: 3, columnGaps: [], type: defaultType }]);
      setError('');
    }
  }, [isOpen, defaultType]);

  const hasDuplicateBlockNames = () => {
    const blockNames = blocks.map(b => b.name.toUpperCase().trim()).filter(Boolean);
    return blockNames.length !== new Set(blockNames).size;
  };

  const isValidBlockName = (name) => {
    const trimmed = name.trim();
    return trimmed.length > 0 && trimmed.length <= 3 && /^[A-Z0-9]+$/i.test(trimmed);
  };

  const addBlock = () => {
    setError('');
    setBlocks([...blocks, {
      id: Date.now(),
      name: '',
      rows: 6,
      cols: 3,
      columnGaps: [],
      type: defaultType
    }]);
  };

  const updateBlock = (id, field, value) => {
    if (field === 'name') {
      const normalizedValue = value.toUpperCase().trim();

      if (normalizedValue && !isValidBlockName(normalizedValue)) {
        setError(`Invalid block name "${normalizedValue}". Use 1-3 alphanumeric characters only.`);
        return;
      }

      const isDuplicate = blocks.some(block =>
        block.id !== id && block.name.toUpperCase().trim() === normalizedValue
      );

      if (isDuplicate) {
        setError(`Block name "${normalizedValue}" already exists.`);
        return;
      }

      setError('');
    }

    setBlocks(blocks.map(block =>
      block.id === id ? { ...block, [field]: value } : block
    ));
  };

  const removeBlock = (id) => {
    setBlocks(blocks.filter(block => block.id !== id));
  };

  const toggleColumnGap = (blockId, colNum) => {
    const block = blocks.find(b => b.id === blockId);
    if (block) {
      const currentGaps = block.columnGaps || [];
      const hasGap = currentGaps.includes(colNum);
      const newGaps = hasGap
        ? currentGaps.filter(g => g !== colNum)
        : [...currentGaps, colNum].sort((a, b) => a - b);
      updateBlock(blockId, 'columnGaps', newGaps);
    }
  };

  const getActiveLocations = (block) => block.rows * block.cols;

  const generateLocations = async () => {
    setLoading(true);
    setError('');

    const invalidBlocks = blocks.filter(b => !isValidBlockName(b.name));
    if (invalidBlocks.length > 0) {
      setError(`Invalid block name(s): ${invalidBlocks.map(b => `"${b.name}"`).join(', ')}.`);
      setLoading(false);
      return;
    }

    if (hasDuplicateBlockNames()) {
      setError('Duplicate block names found. Each block must have a unique name.');
      setLoading(false);
      return;
    }

    try {
      let successCount = 0;

      for (const block of blocks) {
        try {
          await locationService.createBlock({
            name: block.name.toUpperCase().trim(),
            type: block.type || defaultType,
            rows: block.rows,
            cols: block.cols,
            columnGaps: block.columnGaps || []
          });
          successCount++;
        } catch (err) {
          const msg = err.response?.data?.error || err.message;
          console.warn(`Failed to create block ${block.name}:`, msg);
          if (blocks.length === 1) {
            setError(msg);
            setLoading(false);
            return;
          }
        }
      }

      if (onSuccess) onSuccess();
      if (onClose) onClose();
      alert(`Successfully created ${successCount} block(s) with locations`);
    } catch (err) {
      console.error('Error generating locations:', err);
      setError('Failed to generate locations. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white">
          <div>
            <h2 className="text-[20px] font-semibold text-gray-900">
              {defaultType === 'store_shelf' ? 'Store Shelf Builder' : 'Warehouse Map Builder'}
            </h2>
            <p className="text-[12px] text-gray-500 mt-1">
              Design your layout with blocks and generate locations
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Blocks Configuration */}
          <div className="space-y-4 mb-6">
            {blocks.map((block) => (
              <div key={block.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-gray-900">
                    Block {block.name || '?'}
                  </h3>
                  {blocks.length > 1 && (
                    <button
                      onClick={() => removeBlock(block.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Block Name *
                    </label>
                    <input
                      type="text"
                      value={block.name}
                      onChange={(e) => updateBlock(block.id, 'name', e.target.value.toUpperCase())}
                      maxLength={3}
                      className={`w-full px-3 py-2 border rounded-lg text-sm uppercase ${blocks.filter(b => b.name.toUpperCase() === block.name.toUpperCase() && b.name).length > 1
                        ? 'border-red-500 bg-red-50'
                        : 'border-gray-300'
                        }`}
                      placeholder="A"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Rows (Height)
                    </label>
                    <input
                      type="number"
                      value={block.rows}
                      onChange={(e) => updateBlock(block.id, 'rows', parseInt(e.target.value) || 1)}
                      min="1"
                      max="20"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Columns (Width)
                    </label>
                    <input
                      type="number"
                      value={block.cols}
                      onChange={(e) => updateBlock(block.id, 'cols', parseInt(e.target.value) || 1)}
                      min="1"
                      max="20"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    />
                  </div>
                </div>

                {/* Column Gaps Configuration */}
                <div className="mb-4">
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Column Spacing (Visual Only)
                  </label>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-gray-500">Add gap after column:</span>
                    {Array.from({ length: block.cols - 1 }).map((_, idx) => {
                      const colNum = idx + 1;
                      const hasGap = block.columnGaps?.includes(colNum);
                      return (
                        <button
                          key={colNum}
                          onClick={() => toggleColumnGap(block.id, colNum)}
                          className={`px-2 py-1 text-xs rounded border-2 transition-all ${hasGap
                            ? 'bg-blue-500 border-blue-600 text-white'
                            : 'bg-white border-gray-300 text-gray-700 hover:border-blue-400'
                            }`}
                        >
                          {colNum}
                        </button>
                      );
                    })}
                  </div>
                  <p className="text-[10px] text-gray-400 mt-1">
                    Click column numbers to add visual spacing after that column
                  </p>
                </div>

                {/* Preview */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-gray-600">Preview:</p>
                  </div>
                  <div className="inline-block border-2 border-gray-300 rounded">
                    <div className="flex gap-0 p-1 bg-gray-300">
                      {Array.from({ length: block.cols }).map((_, colIdx) => {
                        const hasGapAfter = block.columnGaps?.includes(colIdx + 1);
                        return (
                          <React.Fragment key={colIdx}>
                            <div
                              className="grid gap-[2px]"
                              style={{ gridTemplateRows: `repeat(${block.rows}, 40px)` }}
                            >
                              {Array.from({ length: block.rows }).map((_, rowIdx) => {
                                const position = colIdx * block.rows + rowIdx + 1;
                                const locationName = `${block.name}-${String(position).padStart(2, '0')}`;
                                return (
                                  <div
                                    key={`${rowIdx}-${colIdx}`}
                                    className="bg-white flex items-center justify-center text-[8px] font-mono text-gray-700 border border-gray-200 w-[40px]"
                                    title={locationName}
                                  >
                                    {String(position).padStart(2, '0')}
                                  </div>
                                );
                              })}
                            </div>
                            {hasGapAfter && <div className="w-3 bg-transparent" />}
                          </React.Fragment>
                        );
                      })}
                    </div>
                  </div>
                  <p className="text-[10px] text-gray-500 mt-2">
                    Will generate {getActiveLocations(block)} locations: {block.name || '?'}-01 to {block.name || '?'}-{String(getActiveLocations(block)).padStart(2, '0')}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Add Block Button */}
          <button
            onClick={addBlock}
            className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-emerald-400 hover:text-emerald-600 transition-colors flex items-center justify-center gap-2 mb-6"
          >
            <Plus className="w-4 h-4" />
            Add Another Block
          </button>

          {/* Summary */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h4 className="text-sm font-semibold text-blue-900 mb-2">Summary</h4>
            <div className="text-sm text-blue-800 space-y-1">
              <p>• Total Blocks: {blocks.length}</p>
              <p>• Total Locations: {blocks.reduce((sum, b) => sum + getActiveLocations(b), 0)}</p>
              <p>• Type: {defaultType === 'store_shelf' ? 'Store Shelf' : 'Warehouse'}</p>
              <p className="text-xs text-blue-600 mt-2">
                Locations will be numbered vertically (top to bottom), then left to right.
                Column gaps are saved to database.
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={generateLocations}
              disabled={loading || hasDuplicateBlockNames() || blocks.length === 0 || blocks.some(b => !isValidBlockName(b.name))}
              className="px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Generating...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Generate Locations
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
