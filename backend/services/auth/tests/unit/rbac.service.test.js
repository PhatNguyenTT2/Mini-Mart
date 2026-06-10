/**
 * Unit Tests: RbacService
 * Tests role/permission management with mocked repository.
 */

const RbacService = require('../../src/services/rbac.service');
const { mockRoleRepo, FIXTURES } = require('../helpers');

describe('RbacService', () => {
  let service, roleRepo;

  beforeEach(() => {
    roleRepo = mockRoleRepo();
    service = new RbacService({ roleRepo });
  });

  describe('listRoles()', () => {
    it('should return all roles', async () => {
      roleRepo.findAll.mockResolvedValue([FIXTURES.role]);
      const result = await service.listRoles();
      expect(result.roles).toHaveLength(1);
    });
  });

  describe('createRole()', () => {
    it('should create role with permissions', async () => {
      roleRepo.findByName.mockResolvedValue(null);
      roleRepo.create.mockResolvedValue({ id: 5, name: 'Cashier' });
      roleRepo.findPermissionIdsByCodes.mockResolvedValue([1]);
      roleRepo.findById.mockResolvedValue({ id: 5, name: 'Cashier', permissions: [] });

      const result = await service.createRole({
        roleName: 'Cashier', description: 'POS operator', permissions: ['dashboard.view']
      });

      expect(result.role.roleName).toBe('Cashier');
      expect(roleRepo.findPermissionIdsByCodes).toHaveBeenCalledWith(['dashboard.view']);
    });

    it('should throw ValidationError when name missing', async () => {
      await expect(service.createRole({}))
        .rejects.toThrow('Role name is required');
    });

    it('should throw ConflictError when name exists', async () => {
      roleRepo.findByName.mockResolvedValue(FIXTURES.role);

      await expect(service.createRole({ roleName: 'Super Admin' }))
        .rejects.toThrow('Role name already exists');
    });
  });

  describe('updateRole()', () => {
    it('should update role and permissions', async () => {
      roleRepo.findById.mockResolvedValue(FIXTURES.role);
      roleRepo.findByName.mockResolvedValue(null);
      roleRepo.update.mockResolvedValue({ id: 1, name: 'Admin' });
      roleRepo.findPermissionIdsByCodes.mockResolvedValue([1]);

      await service.updateRole(1, { roleName: 'Admin', permissions: ['dashboard.view'] });

      expect(roleRepo.update).toHaveBeenCalledWith(1, { name: 'Admin', description: undefined });
      expect(roleRepo.findPermissionIdsByCodes).toHaveBeenCalledWith(['dashboard.view']);
    });

    it('should throw NotFoundError when role not found', async () => {
      roleRepo.findById.mockResolvedValue(null);

      await expect(service.updateRole(999, { roleName: 'X' }))
        .rejects.toThrow('Role not found');
    });
  });

  describe('deleteRole()', () => {
    it('should delete role', async () => {
      roleRepo.findById.mockResolvedValue({ ...FIXTURES.role, name: 'Cashier', employee_count: 0 });
      roleRepo.delete.mockResolvedValue(true);

      const result = await service.deleteRole(2);
      expect(result.message).toBe('Role deleted successfully');
    });

    it('should block deleting Super Admin', async () => {
      roleRepo.findById.mockResolvedValue(FIXTURES.role);

      await expect(service.deleteRole(1))
        .rejects.toThrow('Cannot delete Super Admin role');
    });
  });

  describe('listPermissions()', () => {
    it('should return all permissions', async () => {
      roleRepo.getAllPermissions.mockResolvedValue([
        { id: 1, code: 'dashboard.view' }
      ]);

      const result = await service.listPermissions();
      expect(result.permissions).toHaveLength(1);
    });
  });
});
