import React, { useState, useEffect } from 'react';
import { Breadcrumb } from '../components/Breadcrumb';
import { POSAccessList, POSListHeader } from '../components/POSList';
import { EditPOSAccessModal, GrantPOSAccessModal, ViewPOSAccessModal } from '../components/POSList/POSModal';
import posAuthService from '../services/posAuthService';
import settingsService from '../services/settingsService';

export const POSManagement = () => {
  // Breadcrumb items
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'POS Management', href: null },
  ];

  const [posAccess, setPosAccess] = useState([]);
  const [filteredAccess, setFilteredAccess] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortField, setSortField] = useState('fullName');
  const [sortOrder, setSortOrder] = useState('asc');
  const [itemsPerPage, setItemsPerPage] = useState(20);

  // Modal states
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isGrantModalOpen, setIsGrantModalOpen] = useState(false);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);

  // Statistics
  const [stats, setStats] = useState({
    total: 0,
    active: 0,
    locked: 0,
    denied: 0
  });

  // POS Security Settings
  const [posSecuritySettings, setPosSecuritySettings] = useState({
    maxFailedAttempts: 5,
    lockDurationMinutes: 15,
    pinLength: 6
  });

  // Fetch POS access and security settings on mount
  useEffect(() => {
    fetchPOSAccess();
    fetchPOSSecuritySettings();
  }, []);

  // Update filtered data when search, filter, or data changes
  useEffect(() => {
    applyFilters();
  }, [searchQuery, statusFilter, posAccess]);

  // Fetch POS security settings
  const fetchPOSSecuritySettings = async () => {
    try {
      const response = await settingsService.getPOSSecurity();
      if (response.success) {
        setPosSecuritySettings(response.data);
      }
    } catch (err) {
      console.error('Error fetching POS security settings:', err);
      // Use defaults if fetch fails
    }
  };

  // Fetch POS access from API
  const fetchPOSAccess = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await posAuthService.getAllPOSAccess();

      if (response.success) {
        const accessData = response.data || [];
        setPosAccess(accessData);
        calculateStats(accessData);
      } else {
        setError(response.error || 'Failed to fetch POS access data');
      }
    } catch (err) {
      console.error('Error fetching POS access:', err);
      setError(err.response?.data?.error || err.message || 'Failed to fetch POS access data');
    } finally {
      setLoading(false);
    }
  };

  // Calculate statistics
  const calculateStats = (data) => {
    const total = data.length;
    const active = data.filter(a => a.canAccessPOS && !a.isPinLocked).length;
    const locked = data.filter(a => a.isPinLocked).length;
    const denied = data.filter(a => !a.canAccessPOS).length;

    setStats({ total, active, locked, denied });
  };

  // Apply search and filter
  const applyFilters = () => {
    let filtered = [...posAccess];

    // Apply search
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(access => {
        const fullName = access.employee?.fullName?.toLowerCase() || '';
        const idStr = String(access.employee?.id || '');
        return fullName.includes(query) || idStr.includes(query);
      });
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(access => {
        switch (statusFilter) {
          case 'active':
            return access.canAccessPOS && !access.isPinLocked;
          case 'locked':
            return access.isPinLocked;
          case 'denied':
            return !access.canAccessPOS;
          default:
            return true;
        }
      });
    }

    setFilteredAccess(filtered);
  };

  // Handle sort
  const handleSort = (field) => {
    const newSortOrder = sortField === field && sortOrder === 'asc' ? 'desc' : 'asc';
    setSortField(field);
    setSortOrder(newSortOrder);

    const sorted = [...filteredAccess].sort((a, b) => {
      let aVal, bVal;

      switch (field) {
        case 'fullName':
          aVal = a.employee?.fullName || '';
          bVal = b.employee?.fullName || '';
          break;
        case 'id':
          aVal = a.employee?.id || 0;
          bVal = b.employee?.id || 0;
          break;
        case 'status':
          // Active > Locked > Denied
          aVal = a.canAccessPOS && !a.isPinLocked ? 3 : a.isPinLocked ? 2 : 1;
          bVal = b.canAccessPOS && !b.isPinLocked ? 3 : b.isPinLocked ? 2 : 1;
          break;
        case 'posLastLogin':
          aVal = a.posLastLogin ? new Date(a.posLastLogin).getTime() : 0;
          bVal = b.posLastLogin ? new Date(b.posLastLogin).getTime() : 0;
          break;
        case 'pinFailedAttempts':
          aVal = a.pinFailedAttempts || 0;
          bVal = b.pinFailedAttempts || 0;
          break;
        default:
          aVal = a[field] || '';
          bVal = b[field] || '';
      }

      // Handle null values
      if (!aVal && bVal) return 1;
      if (aVal && !bVal) return -1;
      if (!aVal && !bVal) return 0;

      // Convert to lowercase for string comparison
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();

      if (newSortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    setFilteredAccess(sorted);
  };

  // Handle search change
  const handleSearchChange = (query) => {
    setSearchQuery(query);
  };

  // Handle search
  const handleSearch = (query) => {
    // Search is applied via useEffect watching searchQuery
    console.log('Search triggered:', query);
  };

  // Handle filter status
  const handleFilterStatus = (status) => {
    setStatusFilter(status);
  };

  // Handle items per page change
  const handleItemsPerPageChange = (value) => {
    setItemsPerPage(value);
  };

  // Handle grant access
  const handleGrantAccess = () => {
    console.log('Grant POS Access clicked');
    setIsGrantModalOpen(true);
  };

  // Handle grant success
  const handleGrantSuccess = async (newPOSAuth) => {
    try {
      // Show success message
      alert(`POS access granted successfully to ${newPOSAuth.employee?.fullName}`);

      // Refresh data
      await fetchPOSAccess();
    } catch (err) {
      console.error('Error after granting access:', err);
    }
  };

  // Handle view details
  const handleViewDetails = (access) => {
    console.log('View POS details:', access);
    setSelectedEmployee(access);
    setIsViewModalOpen(true);
  };

  // Handle edit settings
  const handleEditSettings = (access) => {
    console.log('Edit POS settings:', access);
    setSelectedEmployee(access);
    setIsEditModalOpen(true);
  };

  // Handle edit success
  const handleEditSuccess = async (updates) => {
    try {
      const employeeId = selectedEmployee.employee.id;

      // Update POS access status
      if (updates.canAccessPOS) {
        await posAuthService.enablePOSAccess(employeeId);
      } else {
        await posAuthService.disablePOSAccess(employeeId);
      }

      // Update PIN if required
      if (updates.requirePINReset && updates.newPIN) {
        await posAuthService.updatePIN(employeeId, updates.newPIN);
      }

      // Show success message
      alert('POS access settings updated successfully');

      // Refresh data
      await fetchPOSAccess();
    } catch (err) {
      console.error('Error updating POS settings:', err);
      throw new Error(err.response?.data?.error?.message || err.message || 'Failed to update POS settings');
    }
  };

  // Handle reset PIN
  const handleResetPIN = (access) => {
    console.log('Reset PIN:', access);
    // TODO: Open ResetPINModal
  };

  // Handle unlock account
  const handleUnlock = async (access) => {
    if (!window.confirm(`Unlock POS access for ${access.employee?.fullName}?`)) {
      return;
    }

    try {
      const response = await posAuthService.resetFailedAttempts(access.employee.id);

      if (response.success) {
        alert('Account unlocked successfully');
        fetchPOSAccess(); // Refresh data
      } else {
        alert(response.error || 'Failed to unlock account');
      }
    } catch (err) {
      console.error('Error unlocking account:', err);
      alert(err.response?.data?.error?.message || err.message || 'Failed to unlock account');
    }
  };

  // Handle revoke access
  const handleRevoke = async (accessId) => {
    try {
      const access = posAccess.find(a => a.id === accessId);

      if (!access) {
        alert('Access record not found');
        return;
      }

      // Check if access is active (not locked, not denied)
      const isActive = access.canAccessPOS && !access.isPinLocked;
      if (!isActive) {
        alert('Can only revoke access for active POS accounts');
        return;
      }

      const response = await posAuthService.disablePOSAccess(access.employee.id);

      if (response.success) {
        alert('POS access revoked successfully');
        fetchPOSAccess(); // Refresh data
      } else {
        alert(response.error || 'Failed to revoke access');
      }
    } catch (err) {
      console.error('Error revoking access:', err);
      alert(err.response?.data?.error?.message || err.message || 'Failed to revoke access');
    }
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px] font-['Poppins',sans-serif]">
          {error}
        </div>
      )}

      {/* POS List Header */}
      <POSListHeader
        itemsPerPage={itemsPerPage}
        onItemsPerPageChange={handleItemsPerPageChange}
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        onSearch={handleSearch}
        onGrantAccess={handleGrantAccess}
        totalPOS={stats.total}
        activePOS={stats.active}
        lockedPOS={stats.locked}
        deniedPOS={stats.denied}
        statusFilter={statusFilter}
        onFilterStatus={handleFilterStatus}
      />

      {/* Loading State */}
      {loading ? (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <div className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-6 w-6 text-emerald-600" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <p className="text-gray-600 text-[14px] font-['Poppins',sans-serif]">
              Loading POS access data...
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* POS Access List */}
          <POSAccessList
            posAccess={filteredAccess}
            onViewDetails={handleViewDetails}
            onEditSettings={handleEditSettings}
            onResetPIN={handleResetPIN}
            onUnlock={handleUnlock}
            onRevoke={handleRevoke}
            onSort={handleSort}
            sortField={sortField}
            sortOrder={sortOrder}
            maxFailedAttempts={posSecuritySettings.maxFailedAttempts}
          />

          {/* Results Summary */}
          {filteredAccess.length > 0 && (
            <div className="text-center text-sm text-gray-600 font-['Poppins',sans-serif]">
              Showing {filteredAccess.length} of {stats.total} POS access record{filteredAccess.length !== 1 ? 's' : ''}
            </div>
          )}

          {/* Empty State */}
          {filteredAccess.length === 0 && !loading && (
            <div className="bg-white rounded-lg shadow-sm p-12 text-center">
              <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
              </svg>
              <p className="text-gray-500 text-[14px] font-['Poppins',sans-serif]">
                No POS access records found
              </p>
            </div>
          )}
        </>
      )}

      {/* Modals */}
      <GrantPOSAccessModal
        isOpen={isGrantModalOpen}
        onClose={() => setIsGrantModalOpen(false)}
        onSuccess={handleGrantSuccess}
      />

      <EditPOSAccessModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        employee={selectedEmployee}
        onSuccess={handleEditSuccess}
      />

      <ViewPOSAccessModal
        isOpen={isViewModalOpen}
        onClose={() => {
          setIsViewModalOpen(false);
          setSelectedEmployee(null);
        }}
        employee={selectedEmployee}
        maxFailedAttempts={posSecuritySettings.maxFailedAttempts}
      />

      {/* TODO: Add more modals
          - ResetPINModal
        */}
    </div>
  );
};

export default POSManagement;
