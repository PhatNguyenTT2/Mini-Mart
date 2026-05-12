import React, { useState, useEffect } from 'react';
import { Breadcrumb } from '../components/Breadcrumb';
import { RolesList, RolesListHeader, AddRolesModal, EditRolesModal, ViewRolesModal } from '../components/RolesList';
import roleService from '../services/roleService';

export const Roles = () => {
  // Breadcrumb items
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Roles', href: null },
  ];

  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [itemsPerPage, setItemsPerPage] = useState(20);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('id');
  const [sortOrder, setSortOrder] = useState('asc');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(false);
  const [selectedRole, setSelectedRole] = useState(null);

  // Fetch roles on mount
  useEffect(() => {
    fetchRoles();
  }, []);

  // Fetch roles from API
  const fetchRoles = async (params = {}) => {
    setLoading(true);
    setError(null);

    try {
      // Include employee count
      const response = await roleService.getAllRoles({
        ...params,
        withEmployees: true
      });

      if (response.success) {
        // Sort by roleCode ascending (default)
        const sortedRoles = (response.data.roles || []).sort((a, b) => {
          return a.id - b.id;
        });

        setRoles(sortedRoles);
      } else {
        setError(response.error || 'Failed to fetch roles');
      }
    } catch (err) {
      console.error('Error fetching roles:', err);
      setError(err.response?.data?.error?.message || err.message || 'Failed to fetch roles');
    } finally {
      setLoading(false);
    }
  };

  // Handle sort (client-side)
  const handleSort = (field) => {
    const newSortOrder = sortField === field && sortOrder === 'asc' ? 'desc' : 'asc';
    setSortField(field);
    setSortOrder(newSortOrder);

    const sortedRoles = [...roles].sort((a, b) => {
      let aVal = a[field] || '';
      let bVal = b[field] || '';

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

    setRoles(sortedRoles);
  };

  // Handle search
  const handleSearch = (query) => {
    setSearchQuery(query);

    if (!query.trim()) {
      fetchRoles();
      return;
    }

    // Search via API
    fetchRoles({ search: query });
  };

  // Handle add role
  const handleAddRole = () => {
    setShowAddModal(true);
  };

  // Handle add success
  const handleAddSuccess = (newRole) => {
    console.log('Role added successfully:', newRole);
    // Refresh the list
    fetchRoles();
  };

  // Handle view details
  const handleViewDetails = (role) => {
    setSelectedRole(role);
    setShowViewModal(true);
  };

  // Handle edit role
  const handleEditRole = (role) => {
    setSelectedRole(role);
    setShowEditModal(true);
  };

  // Handle edit success
  const handleEditSuccess = (updatedRole) => {
    console.log('Role updated successfully:', updatedRole);
    // Refresh the list
    fetchRoles();
  };

  // Handle delete role
  const handleDeleteRole = async (roleId) => {
    if (!window.confirm('Are you sure you want to delete this role?')) {
      return;
    }

    try {
      const response = await roleService.deleteRole(roleId);

      if (response.success) {
        // Remove from local state
        setRoles(roles.filter(role => role.id !== roleId));
        alert('Role deleted successfully');
      } else {
        alert(response.error || 'Failed to delete role');
      }
    } catch (err) {
      console.error('Error deleting role:', err);
      const errorMessage = err.response?.data?.error?.message || err.message || 'Failed to delete role';
      alert(errorMessage);
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

      {/* Roles List Header */}
      <RolesListHeader
        itemsPerPage={itemsPerPage}
        onItemsPerPageChange={setItemsPerPage}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onSearch={handleSearch}
        onAddRole={handleAddRole}
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
              Loading roles...
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* Roles List */}
          <RolesList
            roles={roles}
            onEdit={handleEditRole}
            onDelete={handleDeleteRole}
            onViewDetails={handleViewDetails}
            onSort={handleSort}
            sortField={sortField}
            sortOrder={sortOrder}
          />

          {/* Results Summary */}
          {roles.length > 0 && (
            <div className="text-center text-sm text-gray-600 font-['Poppins',sans-serif]">
              Showing {roles.length} role{roles.length !== 1 ? 's' : ''}
            </div>
          )}

          {/* Empty State */}
          {roles.length === 0 && !loading && (
            <div className="bg-white rounded-lg shadow-sm p-12 text-center">
              <p className="text-gray-500 text-[14px] font-['Poppins',sans-serif]">
                No roles found
              </p>
            </div>
          )}
        </>
      )}

      {/* Add Role Modal */}
      <AddRolesModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handleAddSuccess}
      />

      {/* Edit Role Modal */}
      <EditRolesModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedRole(null);
        }}
        onSuccess={handleEditSuccess}
        role={selectedRole}
      />

      {/* View Role Modal */}
      <ViewRolesModal
        isOpen={showViewModal}
        onClose={() => {
          setShowViewModal(false);
          setSelectedRole(null);
        }}
        role={selectedRole}
      />
    </div>
  );
};

export default Roles;
