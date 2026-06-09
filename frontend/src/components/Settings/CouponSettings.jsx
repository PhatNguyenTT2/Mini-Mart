import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import { Ticket, Plus, Edit2, Trash2, Calendar, FileText, Check, X, Users, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

export const CouponSettings = () => {
  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingCoupon, setEditingCoupon] = useState(null);
  const [showUsageModal, setShowUsageModal] = useState(false);
  const [selectedLogs, setSelectedLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [selectedCouponName, setSelectedCouponName] = useState('');

  // Form State
  const [formData, setFormData] = useState({
    code: '',
    discount_type: 'percent',
    discount_value: '',
    min_order_amount: '0',
    max_discount_amount: '',
    start_date: '',
    end_date: '',
    usage_limit: '',
    is_active: true,
    description: ''
  });

  useEffect(() => {
    loadCoupons();
  }, []);

  const loadCoupons = async () => {
    try {
      setLoading(true);
      const res = await settingsService.getCoupons();
      setCoupons(res.data || res || []);
    } catch (err) {
      console.error('Failed to load coupons:', err);
      toast.error('Failed to load coupons');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenCreate = () => {
    setEditingCoupon(null);
    setFormData({
      code: '',
      discount_type: 'percent',
      discount_value: '',
      min_order_amount: '0',
      max_discount_amount: '',
      start_date: new Date().toISOString().substring(0, 16),
      end_date: '',
      usage_limit: '',
      is_active: true,
      description: ''
    });
    setShowModal(true);
  };

  const handleOpenEdit = (coupon) => {
    setEditingCoupon(coupon);
    setFormData({
      code: coupon.code,
      discount_type: coupon.discount_type,
      discount_value: coupon.discount_value,
      min_order_amount: coupon.min_order_amount || '0',
      max_discount_amount: coupon.max_discount_amount || '',
      start_date: coupon.start_date ? new Date(coupon.start_date).toISOString().substring(0, 16) : '',
      end_date: coupon.end_date ? new Date(coupon.end_date).toISOString().substring(0, 16) : '',
      usage_limit: coupon.usage_limit || '',
      is_active: coupon.is_active,
      description: coupon.description || ''
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.code.trim()) {
      toast.error('Coupon code is required');
      return;
    }

    const payload = {
      code: formData.code.toUpperCase().trim(),
      discount_type: formData.discount_type,
      discount_value: parseFloat(formData.discount_value),
      min_order_amount: parseFloat(formData.min_order_amount || 0),
      max_discount_amount: formData.max_discount_amount ? parseFloat(formData.max_discount_amount) : null,
      start_date: formData.start_date ? new Date(formData.start_date).toISOString() : null,
      end_date: formData.end_date ? new Date(formData.end_date).toISOString() : null,
      usage_limit: formData.usage_limit ? parseInt(formData.usage_limit) : null,
      is_active: formData.is_active,
      description: formData.description
    };

    try {
      if (editingCoupon) {
        await settingsService.updateCoupon(editingCoupon.id, payload);
        toast.success('Coupon updated successfully');
      } else {
        await settingsService.createCoupon(payload);
        toast.success('Coupon created successfully');
      }
      setShowModal(false);
      loadCoupons();
    } catch (err) {
      console.error('Error saving coupon:', err);
      toast.error(err.response?.data?.error?.message || 'Failed to save coupon');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to deactivate/delete this coupon?')) return;
    try {
      await settingsService.deleteCoupon(id);
      toast.success('Coupon deactivated/deleted successfully');
      loadCoupons();
    } catch (err) {
      console.error('Error deleting coupon:', err);
      toast.error('Failed to deactivate coupon');
    }
  };

  const handleToggleActive = async (coupon) => {
    try {
      await settingsService.updateCoupon(coupon.id, {
        ...coupon,
        is_active: !coupon.is_active
      });
      toast.success(`Coupon ${coupon.is_active ? 'deactivated' : 'activated'} successfully`);
      loadCoupons();
    } catch (err) {
      console.error('Error toggling active status:', err);
      toast.error('Failed to change status');
    }
  };

  const handleOpenUsage = async (coupon) => {
    setSelectedCouponName(coupon.code);
    setShowUsageModal(true);
    setLoadingLogs(true);
    try {
      const res = await settingsService.getCouponUsages(coupon.id);
      setSelectedLogs(res.data || res || []);
    } catch (err) {
      console.error('Error loading usages:', err);
      toast.error('Failed to load coupon usage history');
    } finally {
      setLoadingLogs(false);
    }
  };

  const formatVND = (amt) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amt);
  };

  return (
    <div className="space-y-6">
      {/* Search and Action Bar */}
      <div className="flex justify-between items-center gap-4 bg-gray-50 p-4 rounded-xl border border-gray-100">
        <div className="flex items-center gap-2">
          <Ticket className="w-5 h-5 text-emerald-600" />
          <span className="font-semibold text-gray-800 text-sm">Omnichannel Coupons Management</span>
        </div>
        <button
          onClick={handleOpenCreate}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Create Coupon
        </button>
      </div>

      {/* Coupons List */}
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin" />
        </div>
      ) : coupons.length === 0 ? (
        <div className="bg-gray-50 border border-dashed border-gray-200 rounded-xl p-12 text-center">
          <Ticket className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No coupons found. Create your first promotion!</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-150 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-150 text-left text-sm text-gray-700">
            <thead className="bg-gray-50 font-semibold text-gray-650">
              <tr>
                <th className="px-6 py-4">Code</th>
                <th className="px-6 py-4">Type</th>
                <th className="px-6 py-4">Value</th>
                <th className="px-6 py-4">Min spend</th>
                <th className="px-6 py-4">Usage Count</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Validity</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {coupons.map((coupon) => {
                const now = new Date();
                const start = coupon.start_date ? new Date(coupon.start_date) : null;
                const end = coupon.end_date ? new Date(coupon.end_date) : null;
                const isExpired = end && now > end;
                const isNotStarted = start && now < start;
                const isLimitReached = coupon.usage_limit && coupon.usage_count >= coupon.usage_limit;

                return (
                  <tr key={coupon.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 font-bold text-gray-900 tracking-wider">
                      {coupon.code}
                    </td>
                    <td className="px-6 py-4 uppercase font-medium text-xs">
                      {coupon.discount_type}
                    </td>
                    <td className="px-6 py-4 font-semibold text-emerald-600">
                      {coupon.discount_type === 'percent' ? `${coupon.discount_value}%` : formatVND(coupon.discount_value)}
                    </td>
                    <td className="px-6 py-4 text-gray-550">
                      {formatVND(coupon.min_order_amount || 0)}
                    </td>
                    <td className="px-6 py-4 text-gray-550">
                      <span className="font-semibold">{coupon.usage_count}</span>
                      {coupon.usage_limit ? ` / ${coupon.usage_limit}` : ' / ♾️'}
                    </td>
                    <td className="px-6 py-4">
                      {coupon.is_active && !isExpired && !isLimitReached && !isNotStarted ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-green-50 text-green-700 rounded-full text-xs font-semibold">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-50 text-red-700 rounded-full text-xs font-semibold">
                          {isExpired ? 'Expired' : isNotStarted ? 'Scheduled' : isLimitReached ? 'Limit Reached' : 'Inactive'}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-450 whitespace-nowrap">
                      {start ? start.toLocaleDateString() : 'N/A'} - {end ? end.toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleOpenUsage(coupon)}
                          title="View Usages Log"
                          className="p-1.5 text-blue-650 hover:bg-blue-50 rounded transition-colors"
                        >
                          <Users className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleOpenEdit(coupon)}
                          title="Edit Coupon"
                          className="p-1.5 text-gray-500 hover:bg-gray-100 rounded transition-colors"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleToggleActive(coupon)}
                          title={coupon.is_active ? 'Deactivate' : 'Activate'}
                          className={`p-1.5 rounded transition-colors ${coupon.is_active ? 'text-amber-600 hover:bg-amber-50' : 'text-emerald-600 hover:bg-emerald-50'}`}
                        >
                          {coupon.is_active ? <X className="w-4 h-4" /> : <Check className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => handleDelete(coupon.id)}
                          title="Delete Coupon"
                          className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* CREATE/EDIT MODAL */}
      {showModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-gray-100 max-w-lg w-full overflow-hidden">
            <div className="bg-gray-50 px-6 py-4 border-b border-gray-150 flex justify-between items-center">
              <h3 className="font-bold text-gray-800 text-lg">
                {editingCoupon ? `Edit Coupon: ${editingCoupon.code}` : 'Create New Coupon'}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Coupon Code</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. WELCOME2026"
                  disabled={!!editingCoupon}
                  value={formData.code}
                  onChange={(e) => setFormData(prev => ({ ...prev, code: e.target.value.toUpperCase() }))}
                  className="w-full px-4 py-2 border border-gray-250 rounded-lg text-sm uppercase tracking-wider font-bold focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Discount Type</label>
                  <select
                    value={formData.discount_type}
                    onChange={(e) => setFormData(prev => ({ ...prev, discount_type: e.target.value }))}
                    className="w-full px-4 py-2 border border-gray-250 rounded-lg text-sm bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  >
                    <option value="percent">Percent (%)</option>
                    <option value="fixed">Fixed Cash (VND)</option>
                    <option value="freeship">Free Shipping</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Discount Value</label>
                  <input
                    type="number"
                    required
                    min="0"
                    placeholder={formData.discount_type === 'percent' ? 'e.g. 10' : 'e.g. 20000'}
                    value={formData.discount_value}
                    onChange={(e) => setFormData(prev => ({ ...prev, discount_value: e.target.value }))}
                    className="w-full px-4 py-2 border border-gray-250 rounded-lg text-sm font-semibold focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Min Order Spend</label>
                  <input
                    type="number"
                    min="0"
                    placeholder="e.g. 50000"
                    value={formData.min_order_amount}
                    onChange={(e) => setFormData(prev => ({ ...prev, min_order_amount: e.target.value }))}
                    className="w-full px-4 py-2 border border-gray-250 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Limit Max Cap (VND)</label>
                  <input
                    type="number"
                    min="0"
                    placeholder="Uncapped"
                    value={formData.max_discount_amount}
                    onChange={(e) => setFormData(prev => ({ ...prev, max_discount_amount: e.target.value }))}
                    className="w-full px-4 py-2 border border-gray-250 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Start Date</label>
                  <input
                    type="datetime-local"
                    value={formData.start_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, start_date: e.target.value }))}
                    className="w-full px-4 py-2 border border-gray-250 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">End Date (Expiry)</label>
                  <input
                    type="datetime-local"
                    value={formData.end_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, end_date: e.target.value }))}
                    className="w-full px-4 py-2 border border-gray-250 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Usage Limit (Times)</label>
                  <input
                    type="number"
                    min="1"
                    placeholder="Unlimited"
                    value={formData.usage_limit}
                    onChange={(e) => setFormData(prev => ({ ...prev, usage_limit: e.target.value }))}
                    className="w-full px-4 py-2 border border-gray-250 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
                <div className="flex items-center pt-6">
                  <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.is_active}
                      onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                      className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 h-4 w-4"
                    />
                    Is Active Currently
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5">Display Description</label>
                <textarea
                  placeholder="Provide details for customer display..."
                  rows="2"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full px-4 py-2 border border-gray-250 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none resize-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-150">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-150 rounded-lg text-sm font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-colors shadow-sm"
                >
                  {editingCoupon ? 'Save Changes' : 'Create Coupon'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* USAGE LOGS DETAILS MODAL */}
      {showUsageModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-gray-100 max-w-2xl w-full overflow-hidden">
            <div className="bg-gray-50 px-6 py-4 border-b border-gray-150 flex justify-between items-center">
              <h3 className="font-bold text-gray-800 text-lg flex items-center gap-2">
                <Users className="w-5 h-5 text-emerald-605" />
                Usage History: <span className="text-emerald-700 underline">{selectedCouponName}</span>
              </h3>
              <button
                onClick={() => setShowUsageModal(false)}
                className="text-gray-400 hover:text-gray-650"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6">
              {loadingLogs ? (
                <div className="flex justify-center items-center py-12">
                  <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin" />
                </div>
              ) : selectedLogs.length === 0 ? (
                <div className="text-center py-12 bg-gray-50 border border-dashed border-gray-200 rounded-xl">
                  <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500 font-medium">This coupon has not been used in any orders yet.</p>
                </div>
              ) : (
                <div className="border border-gray-150 rounded-lg overflow-hidden max-h-96 overflow-y-auto">
                  <table className="min-w-full divide-y divide-gray-150 text-left text-xs text-gray-750">
                    <thead className="bg-gray-50 font-bold">
                      <tr>
                        <th className="px-4 py-3">Order ID</th>
                        <th className="px-4 py-3">Customer ID</th>
                        <th className="px-4 py-3">Applied At</th>
                        <th className="px-4 py-3 text-right">Discount Amt</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {selectedLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-semibold text-gray-900">
                            #{log.order_id}
                          </td>
                          <td className="px-4 py-3 text-gray-500">
                            {log.customer_id}
                          </td>
                          <td className="px-4 py-3 text-gray-450">
                            {new Date(log.used_at).toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-right font-semibold text-emerald-600">
                            {formatVND(log.discount_applied)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="bg-gray-50 px-6 py-4 border-t border-gray-150 flex justify-end">
              <button
                type="button"
                onClick={() => setShowUsageModal(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-650 text-white rounded-lg text-sm font-semibold transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
