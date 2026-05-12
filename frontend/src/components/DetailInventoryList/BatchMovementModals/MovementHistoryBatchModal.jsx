import React, { useState, useEffect } from 'react';
import inventoryMovementBatchService from '../../../services/inventoryMovementBatchService';
import employeeService from '../../../services/employeeService';

export const MovementHistoryBatchModal = ({ isOpen, onClose, detailInventory }) => {
  const [movements, setMovements] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [employeeMap, setEmployeeMap] = useState({});

  useEffect(() => {
    if (isOpen && detailInventory) {
      fetchMovements();
    }
  }, [isOpen, detailInventory]);

  const fetchMovements = async () => {
    setLoading(true);
    setError(null);

    try {
      const itemId = detailInventory.id;
      const response = await inventoryMovementBatchService.getMovementsByItem(itemId);

      if (response.success && Array.isArray(response.data)) {
        setMovements(response.data);
        resolveEmployeeNames(response.data);
      } else {
        setMovements([]);
      }
    } catch (err) {
      console.error('Error fetching movements:', err);
      setError(err.message || 'Failed to load movement history');
      setMovements([]);
    } finally {
      setLoading(false);
    }
  };

  const resolveEmployeeNames = async (movementList) => {
    const uniqueIds = [...new Set(
      movementList.map(m => m.performedBy).filter(Boolean)
    )];
    if (uniqueIds.length === 0) return;

    const map = {};
    await Promise.all(uniqueIds.map(async (id) => {
      try {
        const res = await employeeService.getEmployeeById(id);
        const emp = res.data || res;
        map[id] = emp.full_name || emp.fullName || emp.username || `User #${id}`;
      } catch {
        map[id] = `User #${id}`;
      }
    }));
    setEmployeeMap(prev => ({ ...prev, ...map }));
  };

  if (!isOpen) return null;

  const filteredMovements = (() => {
    if (filter === 'all') return movements;
    // Map 'location' type to 'adjustment' for filtering since location changes are displayed as adjustments
    if (filter === 'adjustment') {
      return movements.filter(m => m.movementType === 'adjustment' || m.movementType === 'location');
    }
    return movements.filter(m => m.movementType === filter);
  })();

  const getMovementTypeBadge = (type) => {
    const badges = {
      'in': { bg: 'bg-green-100', text: 'text-green-700', label: 'Stock In' },
      'out': { bg: 'bg-red-100', text: 'text-red-700', label: 'Stock Out' },
      'adjustment': { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Adjustment' },
      'transfer': { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Transfer' },
      'reserve': { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Reserved' },
      'release': { bg: 'bg-teal-100', text: 'text-teal-700', label: 'Released' }
    };

    const badge = badges[type] || badges['adjustment'];

    return (
      <span className={`${badge.bg} ${badge.text} px-2 py-1 rounded text-[10px] font-bold font-['Poppins',sans-serif] uppercase`}>
        {badge.label}
      </span>
    );
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatQuantity = (movement) => {
    const quantity = movement.quantity;
    const type = movement.movementType;

    if (type === 'in') {
      return `+${Math.abs(quantity)}`;
    } else if (type === 'out') {
      return `-${Math.abs(quantity)}`;
    } else if (type === 'adjustment' || type === 'audit') {
      return quantity > 0 ? `+${quantity}` : `${quantity}`;
    } else if (type === 'transfer') {
      return quantity > 0 ? `+${quantity} (→ shelf)` : `${quantity} (→ warehouse)`;
    }
    return quantity;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              Movement History
            </h2>
            <p className="text-[13px] text-gray-600 font-['Poppins',sans-serif] mt-1">
              Batch: {detailInventory?.batchId?.batchCode}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-2 px-6 py-3 border-b border-gray-200">
          {[
            { value: 'all', label: 'All' },
            { value: 'in', label: 'Stock In' },
            { value: 'out', label: 'Stock Out' },
            { value: 'adjustment', label: 'Adjustments' },
            { value: 'transfer', label: 'Transfers' },
            { value: 'audit', label: 'Audits' }
          ].map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-['Poppins',sans-serif] font-medium transition-colors ${filter === value
                ? 'bg-emerald-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px]">
              {error}
            </div>
          )}

          {!loading && !error && filteredMovements.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500 text-[14px] font-['Poppins',sans-serif]">
                No movement history found
              </p>
            </div>
          )}

          {!loading && !error && filteredMovements.length > 0 && (
            <div className="space-y-3">
              {filteredMovements.map((movement, index) => (
                <div
                  key={movement.id || index}
                  className="bg-gray-50 border border-gray-200 rounded-lg p-4 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        {getMovementTypeBadge(movement.movementType)}
                        <span className="text-[13px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
                          {formatQuantity(movement)} units
                        </span>
                        <span className="text-[12px] text-gray-500 font-['Poppins',sans-serif]">
                          {formatDate(movement.movedAt)}
                        </span>
                      </div>

                      {movement.reason && (
                        <p className="text-[13px] text-gray-700 font-['Poppins',sans-serif] mb-1">
                          <span className="font-medium">Reason:</span> {movement.reason}
                        </p>
                      )}

                      {movement.performedBy && (
                        <p className="text-[11px] text-gray-500 font-['Poppins',sans-serif] mt-2">
                          By: {employeeMap[movement.performedBy] || `User #${movement.performedBy}`}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
          <p className="text-[12px] text-gray-600 font-['Poppins',sans-serif]">
            {filteredMovements.length} {filteredMovements.length === 1 ? 'movement' : 'movements'} found
          </p>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-[13px] font-['Poppins',sans-serif] font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
