import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import { Ticket, Plus, Edit2, Trash2, Calendar, FileText, Check, X, Users, RefreshCw, AlertCircle } from 'lucide-react';

export const CouponSettings = () => {
  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingCoupon, setEditingCoupon] = useState(null);
  const [showUsageModal, setShowUsageModal] = useState(false);
  const [selectedLogs, setSelectedLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [selectedCouponName, setSelectedCouponName] = useState('');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

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

  const showError = (msg) => {
    setError(msg);
    setSuccess(null);
    setTimeout(() => setError(null), 4000);
  };

  const showSuccess = (msg) => {
    setSuccess(msg);
    setError(null);
    setTimeout(() => setSuccess(null), 4000);
  };

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
      showError('Failed to load coupons');
    } finally {
      setLoading(false);
    }
  };

  const formatDateTimeLocal = (dateString) => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return '';
      const offset = date.getTimezoneOffset();
      const localDate = new Date(date.getTime() - offset * 60 * 1000);
      return localDate.toISOString().substring(0, 16);
    } catch (err) {
      console.error('Error formatting date:', err);
      return '';
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
      start_date: formatDateTimeLocal(new Date()),
      end_date: '',
      usage_limit: '',
      is_active: true,
      description: ''
    });
    setShowModal(true);
  };

  const handleOpenEdit = (coupon) => {
    setEditingCoupon(coupon);
    const startDate = coupon.starts_at || coupon.start_date;
    const endDate = coupon.expires_at || coupon.end_date;
    const usageLimit = coupon.max_uses !== undefined && coupon.max_uses !== null ? coupon.max_uses : coupon.usage_limit;

    setFormData({
      code: coupon.code,
      discount_type: coupon.discount_type,
      discount_value: coupon.discount_value,
      min_order_amount: coupon.min_order_amount || '0',
      max_discount_amount: coupon.max_discount_amount || '',
      start_date: formatDateTimeLocal(startDate),
      end_date: formatDateTimeLocal(endDate),
      usage_limit: usageLimit !== null && usageLimit !== undefined ? usageLimit : '',
      is_active: coupon.is_active,
      description: coupon.description || ''
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.code.trim()) {
      showError('Coupon code is required');
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
        showSuccess('Coupon updated successfully');
      } else {
        await settingsService.createCoupon(payload);
        showSuccess('Coupon created successfully');
      }
      setShowModal(false);
      loadCoupons();
    } catch (err) {
      console.error('Error saving coupon:', err);
      showError(err.response?.data?.error?.message || 'Failed to save coupon');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to deactivate/delete this coupon?')) return;
    try {
      await settingsService.deleteCoupon(id);
      showSuccess('Coupon deactivated/deleted successfully');
      loadCoupons();
    } catch (err) {
      console.error('Error deleting coupon:', err);
      showError('Failed to deactivate coupon');
    }
  };

  const handleToggleActive = async (coupon) => {
    try {
      await settingsService.updateCoupon(coupon.id, {
        ...coupon,
        is_active: !coupon.is_active
      });
      showSuccess(`Coupon ${coupon.is_active ? 'deactivated' : 'activated'} successfully`);
      loadCoupons();
    } catch (err) {
      console.error('Error toggling active status:', err);
      showError('Failed to change status');
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
      showError('Failed to load coupon usage history');
    } finally {
      setLoadingLogs(false);
    }
  };

  const formatVND = (amt) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amt);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 font-['Poppins',sans-serif]">
            Omnichannel Coupons Management
          </h2>
          <p className="text-sm text-gray-500 mt-1 font-['Poppins',sans-serif]">
            Manage system discount codes, usage limits, and customer promotion history
          </p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-colors shadow-sm font-['Poppins',sans-serif]"
        >
          <Plus className="w-4 h-4" />
          Create Coupon
        </button>
      </div>

      {/* Alert Banner */}
      {(error || success) && (
        <div className={`p-4 rounded-lg flex items-center gap-3 ${error ? 'bg-red-50 text-red-700 border border-red-100' : 'bg-green-50 text-green-700 border border-green-100'} font-['Poppins',sans-serif]`}>
          {error ? <AlertCircle className="w-5 h-5" /> : <Check className="w-5 h-5" />}
          <span className="font-medium">{error || success}</span>
        </div>
      )}

      {/* Coupons List Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-6 font-['Poppins',sans-serif]">
          <Ticket className="w-5 h-5 text-emerald-600" />
          Coupons List
        </h3>

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin" />
          </div>
        ) : coupons.length === 0 ? (
          <div className="bg-gray-50 border border-dashed border-gray-200 rounded-xl p-12 text-center">
            <Ticket className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 font-medium font-['Poppins',sans-serif]">No coupons found. Create your first promotion!</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 h-[34px]">
                  <th className="px-4 text-left text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">Code</th>
                  <th className="px-4 text-left text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">Type</th>
                  <th className="px-4 text-left text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">Value</th>
                  <th className="px-4 text-left text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">Min spend</th>
                  <th className="px-4 text-left text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">Usage Count</th>
                  <th className="px-4 text-left text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">Status</th>
                  <th className="px-4 text-left text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">Validity</th>
                  <th className="px-4 text-center text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {coupons.map((coupon) => {
                  const now = new Date();
                  const startVal = coupon.starts_at || coupon.start_date;
                  const endVal = coupon.expires_at || coupon.end_date;
                  const usageLimit = coupon.max_uses !== undefined && coupon.max_uses !== null ? coupon.max_uses : coupon.usage_limit;
                  const usageCount = coupon.used_count !== undefined && coupon.used_count !== null ? coupon.used_count : (coupon.usage_count ?? 0);

                  const start = startVal ? new Date(startVal) : null;
                  const end = endVal ? new Date(endVal) : null;
                  const isExpired = end && now > end;
                  const isNotStarted = start && now < start;
                  const isLimitReached = usageLimit && usageCount >= usageLimit;

                  return (
                    <tr key={coupon.id} className="hover:bg-emerald-50/50 transition-colors">
                      <td className="px-4 py-3 font-bold text-gray-900 tracking-wider font-mono text-[13px]">
                        {coupon.code}
                      </td>
                      <td className="px-4 py-3 uppercase font-medium text-[12px] text-gray-600 font-['Poppins',sans-serif]">
                        {coupon.discount_type}
                      </td>
                      <td className="px-4 py-3 font-semibold text-emerald-600 text-[13px] font-['Poppins',sans-serif]">
                        {coupon.discount_type === 'percent' ? `${coupon.discount_value}%` : formatVND(coupon.discount_value)}
                      </td>
                      <td className="px-4 py-3 text-[13px] text-gray-600 font-['Poppins',sans-serif]">
                        {formatVND(coupon.min_order_amount || 0)}
                      </td>
                      <td className="px-4 py-3 text-[13px] text-gray-600 font-['Poppins',sans-serif]">
                        <span className="font-semibold text-gray-950">{usageCount}</span>
                        {usageLimit ? ` / ${usageLimit}` : ' / ♾️'}
                      </td>
                      <td className="px-4 py-3 text-[13px] font-['Poppins',sans-serif]">
                        {coupon.is_active && !isExpired && !isLimitReached && !isNotStarted ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-green-50 text-green-700 rounded-full text-xs font-semibold">
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-red-50 text-red-700 rounded-full text-xs font-semibold">
                            {isExpired ? 'Expired' : isNotStarted ? 'Scheduled' : isLimitReached ? 'Limit Reached' : 'Inactive'}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-[12px] text-gray-500 font-['Poppins',sans-serif] whitespace-nowrap">
                        {start ? start.toLocaleDateString() : 'N/A'} - {end ? end.toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex items-center justify-center gap-4">
                          <button
                            onClick={() => handleOpenUsage(coupon)}
                            title="View Usages Log"
                            className="text-[#212529] hover:opacity-85 transition-opacity"
                          >
                            <Users className="w-[18px] h-[18px]" />
                          </button>
                          <button
                            onClick={() => handleOpenEdit(coupon)}
                            title="Edit Coupon"
                            className="text-[#4b5563] hover:opacity-85 transition-opacity"
                          >
                            <Edit2 className="w-[18px] h-[18px]" />
                          </button>
                          <button
                            onClick={() => handleToggleActive(coupon)}
                            title={coupon.is_active ? 'Deactivate' : 'Activate'}
                            className={`transition-opacity hover:opacity-85 ${coupon.is_active ? 'text-[#D97706]' : 'text-emerald-600'}`}
                          >
                            {coupon.is_active ? <X className="w-[18px] h-[18px]" /> : <Check className="w-[18px] h-[18px]" />}
                          </button>
                          <button
                            onClick={() => handleDelete(coupon.id)}
                            title="Delete Coupon"
                            className="text-[#DC2626] hover:opacity-85 transition-opacity"
                          >
                            <Trash2 className="w-[18px] h-[18px]" />
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
      </div>

      {/* CREATE/EDIT MODAL */}
      {showModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-gray-100 max-w-lg w-full overflow-hidden font-['Poppins',sans-serif]">
            <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="font-bold text-gray-900 text-lg font-['Poppins',sans-serif]">
                {editingCoupon ? `Edit Coupon: ${editingCoupon.code}` : 'Create New Coupon'}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5 tracking-wider font-['Poppins',sans-serif]">Coupon Code</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. WELCOME2026"
                  disabled={!!editingCoupon}
                  value={formData.code}
                  onChange={(e) => setFormData(prev => ({ ...prev, code: e.target.value.toUpperCase() }))}
                  className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm uppercase tracking-wider font-bold focus:ring-2 focus:ring-emerald-500 focus:border-transparent focus:outline-none transition-all font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5 tracking-wider font-['Poppins',sans-serif]">Discount Type</label>
                  <select
                    value={formData.discount_type}
                    onChange={(e) => setFormData(prev => ({ ...prev, discount_type: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-emerald-500 focus:border-transparent focus:outline-none transition-all font-['Poppins',sans-serif]"
                  >
                    <option value="percent">Percent (%)</option>
                    <option value="fixed">Fixed Cash (VND)</option>
                    <option value="freeship">Free Shipping</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5 tracking-wider font-['Poppins',sans-serif]">Discount Value</label>
                  <input
                    type="number"
                    required
                    min="0"
                    placeholder={formData.discount_type === 'percent' ? 'e.g. 10' : 'e.g. 20000'}
                    value={formData.discount_value}
                    onChange={(e) => setFormData(prev => ({ ...prev, discount_value: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm font-semibold focus:ring-2 focus:ring-emerald-500 focus:border-transparent focus:outline-none transition-all font-['Poppins',sans-serif]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5 tracking-wider font-['Poppins',sans-serif]">Min Order Spend</label>
                  <input
                    type="number"
                    min="0"
                    placeholder="e.g. 50000"
                    value={formData.min_order_amount}
                    onChange={(e) => setFormData(prev => ({ ...prev, min_order_amount: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent focus:outline-none transition-all font-['Poppins',sans-serif]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5 tracking-wider font-['Poppins',sans-serif]">Limit Max Cap (VND)</label>
                  <input
                    type="number"
                    min="0"
                    placeholder="Uncapped"
                    value={formData.max_discount_amount}
                    onChange={(e) => setFormData(prev => ({ ...prev, max_discount_amount: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent focus:outline-none transition-all font-['Poppins',sans-serif]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5 tracking-wider font-['Poppins',sans-serif]">Start Date</label>
                  <input
                    type="datetime-local"
                    value={formData.start_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, start_date: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent focus:outline-none transition-all font-['Poppins',sans-serif]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5 tracking-wider font-['Poppins',sans-serif]">End Date (Expiry)</label>
                  <input
                    type="datetime-local"
                    value={formData.end_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, end_date: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent focus:outline-none transition-all font-['Poppins',sans-serif]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5 tracking-wider font-['Poppins',sans-serif]">Usage Limit (Times)</label>
                  <input
                    type="number"
                    min="1"
                    placeholder="Unlimited"
                    value={formData.usage_limit}
                    onChange={(e) => setFormData(prev => ({ ...prev, usage_limit: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent focus:outline-none transition-all font-['Poppins',sans-serif]"
                  />
                </div>
                <div className="flex items-center pt-6">
                  <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 cursor-pointer font-['Poppins',sans-serif]">
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
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1.5 tracking-wider font-['Poppins',sans-serif]">Display Description</label>
                <textarea
                  placeholder="Provide details for customer display..."
                  rows="2"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent focus:outline-none transition-all font-['Poppins',sans-serif] resize-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2.5 text-gray-700 hover:bg-gray-100 rounded-lg text-sm font-medium transition-colors font-['Poppins',sans-serif]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm font-['Poppins',sans-serif]"
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
          <div className="bg-white rounded-xl shadow-xl border border-gray-100 max-w-2xl w-full overflow-hidden font-['Poppins',sans-serif]">
            <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="font-bold text-gray-800 text-lg flex items-center gap-2 font-['Poppins',sans-serif]">
                <Users className="w-5 h-5 text-emerald-650" />
                Usage History: <span className="text-emerald-700 underline">{selectedCouponName}</span>
              </h3>
              <button
                onClick={() => setShowUsageModal(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
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
                  <p className="text-gray-500 font-medium font-['Poppins',sans-serif]">This coupon has not been used in any orders yet.</p>
                </div>
              ) : (
                <div className="border border-gray-200 rounded-lg overflow-hidden max-h-96 overflow-y-auto">
                  <table className="min-w-full divide-y divide-gray-150 text-left text-xs text-gray-750">
                    <thead className="bg-gray-50 font-bold border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-3 text-[11px] font-semibold font-['Poppins',sans-serif] text-gray-500 uppercase tracking-[0.5px]">Order ID</th>
                        <th className="px-4 py-3 text-[11px] font-semibold font-['Poppins',sans-serif] text-gray-500 uppercase tracking-[0.5px]">Customer ID</th>
                        <th className="px-4 py-3 text-[11px] font-semibold font-['Poppins',sans-serif] text-gray-500 uppercase tracking-[0.5px]">Applied At</th>
                        <th className="px-4 py-3 text-right text-[11px] font-semibold font-['Poppins',sans-serif] text-gray-500 uppercase tracking-[0.5px]">Discount Amt</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {selectedLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-emerald-50/50 transition-colors">
                          <td className="px-4 py-3 font-semibold text-gray-900 font-mono text-[13px]">
                            #{log.order_id}
                          </td>
                          <td className="px-4 py-3 text-gray-500 font-['Poppins',sans-serif]">
                            {log.customer_id}
                          </td>
                          <td className="px-4 py-3 text-gray-450 font-['Poppins',sans-serif]">
                            {new Date(log.used_at).toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-right font-semibold text-emerald-600 font-['Poppins',sans-serif]">
                            {formatVND(log.discount_applied)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex justify-end">
              <button
                type="button"
                onClick={() => setShowUsageModal(false)}
                className="px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors font-['Poppins',sans-serif]"
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
