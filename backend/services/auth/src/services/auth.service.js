const bcrypt = require('bcrypt');
const crypto = require('crypto');
const { generateToken } = require('../../../../shared/auth-middleware');
const { UnauthorizedError, ValidationError, ConflictError, PinInvalidError, PinLockedError } = require('../../../../shared/common/errors');
const { SALT_ROUNDS, TOKEN_EXPIRY } = require('../../../../shared/common/constants');

class AuthService {
  constructor({ userRepo, authRepo, employeeRepo, customerRepo, roleRepo, storeRepo, pool }) {
    this.userRepo = userRepo;
    this.authRepo = authRepo;
    this.employeeRepo = employeeRepo;
    this.customerRepo = customerRepo;
    this.roleRepo = roleRepo;
    this.storeRepo = storeRepo;
    this.pool = pool;
  }

  async login({ username, password }) {
    if (!username || !password) {
      throw new ValidationError('Username and password are required');
    }

    const user = await this.userRepo.findByUsernameOrEmail(username);
    if (!user) throw new UnauthorizedError('Invalid username or password');
    if (!user.is_active) throw new UnauthorizedError('Account is inactive');

    const valid = await bcrypt.compare(password, user.password_hash);
    if (!valid) throw new UnauthorizedError('Invalid username or password');

    const permissions = await this.userRepo.getPermissions(user.id);
    
    const isCustomer = user.role_name === 'Customer';
    let profile = null;
    let tokenPayload = {
      id: user.id,
      username: user.username,
      role: user.role_id,
      roleName: user.role_name || 'Employee',
      permissions,
      storeId: null
    };

    if (isCustomer) {
      profile = await this.customerRepo.findByUserId(user.id);
      // Include customer table PK so frontend uses correct ID for orders
      tokenPayload.customerId = profile?.id || null;
    } else {
      profile = await this.employeeRepo.findById(user.id);
      tokenPayload.storeId = profile?.store_id || null;
    }

    const token = generateToken(tokenPayload);

    await this.userRepo.updateLastLogin(user.id);

    const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
    await this.authRepo.saveToken({
      userId: user.id,
      tokenHash,
      type: 'REFRESH',
      expiresAt: new Date(Date.now() + TOKEN_EXPIRY.REFRESH_MS)
    });

    return {
      token,
      user: this._formatUserResponse(user, profile, permissions, isCustomer)
    };
  }

  /**
   * Trial Registration (Public API for testing)
   * Creates: Chain Owner + Store + Employee profile in one transaction
   */
  async registerTrial({ username, email, fullName, password, storeName, storeAddress, storePhone }) {
    if (!username || !email || !fullName || !password) {
      throw new ValidationError('All fields required (username, email, fullName, password)');
    }
    if (!storeName) {
      throw new ValidationError('storeName is required for trial registration');
    }
    if (password.length < 6) {
      throw new ValidationError('Password must be at least 6 characters');
    }

    const existingUser = await this.userRepo.findByUsername(username);
    if (existingUser) throw new ConflictError('Username already exists');

    const existingEmail = await this.userRepo.findByEmail(email);
    if (existingEmail) throw new ConflictError('Email already exists');

    const passwordHash = await bcrypt.hash(password, SALT_ROUNDS);

    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');

      // 1. Get Super Admin role
      const role = await this.roleRepo.findByName('Super Admin');
      if (!role) throw new Error('Super Admin role not found. Run init.sql first.');

      // 2. Create user account
      const newUser = await this.userRepo.createWithClient(client, {
        username, email, passwordHash, roleId: role.id
      });

      // 3. Create store
      const newStore = await this.storeRepo.createWithClient(client, {
        name: storeName,
        address: storeAddress || null,
        phone: storePhone || null,
        manager_id: newUser.id
      });

      // 4. Create employee profile linked to store
      await this.employeeRepo.createProfile(client, newUser.id, newStore.id, {
        full_name: fullName
      });

      await client.query('COMMIT');

      return {
        id: newUser.id,
        username: newUser.username,
        email: newUser.email,
        fullName,
        role: 'Super Admin',
        store: {
          id: newStore.id,
          name: newStore.name
        }
      };
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }

  /**
   * Customer Self-Registration (Public API for online web store)
   * Creates: user_account (role=Customer) + customer profile, returns JWT for immediate use
   */
  async registerCustomer({ fullName, username, email, password, phone, address, gender, dob }) {
    if (!fullName || !email || !password) {
      throw new ValidationError('fullName, email, and password are required');
    }
    if (password.length < 6) {
      throw new ValidationError('Password must be at least 6 characters');
    }

    const existingEmail = await this.userRepo.findByEmail(email);
    if (existingEmail) throw new ConflictError('Email already exists');

    // Use provided username or auto-generate from email
    const finalUsername = username || email.split('@')[0] + '_' + Date.now().toString(36);

    if (username) {
      const existingUsername = await this.userRepo.findByUsername(username);
      if (existingUsername) throw new ConflictError('Username already exists');
    }

    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');

      // Get or create Customer role
      let role = await this.roleRepo.findByName('Customer');
      if (!role) {
        role = await this.roleRepo.create({ name: 'Customer', description: 'Customer role' });
      }

      const passwordHash = await bcrypt.hash(password, SALT_ROUNDS);

      const newUser = await this.userRepo.createWithClient(client, {
        username: finalUsername, email, passwordHash, roleId: role.id
      });

      const customerProfile = await this.customerRepo.create(client, {
        userId: newUser.id, fullName, phone, address, gender, dob, customerType: 'retail'
      });

      await client.query('COMMIT');

      // Auto-login: generate token for immediate use
      const permissions = await this.userRepo.getPermissions(newUser.id);
      const token = generateToken({
        id: newUser.id,
        username: finalUsername,
        role: role.id,
        roleName: 'Customer',
        permissions,
        storeId: null,
        customerId: customerProfile.id
      });

      return {
        token,
        user: {
          id: newUser.id,
          customerId: customerProfile.id,
          username: finalUsername,
          email,
          fullName,
          phone: phone || '',
          address: address || '',
          dob: dob || null,
          role: 'Customer'
        }
      };
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }

  async logout(token) {
    const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
    await this.authRepo.deleteToken(tokenHash);
  }

  async getMe(userId) {
    const user = await this.userRepo.findById(userId);
    if (!user || !user.is_active) throw new UnauthorizedError('User not found or inactive');

    const permissions = await this.userRepo.getPermissions(userId);
    let profile = null;
    let isCustomer = false;

    if (user.role_name === 'Customer') {
      profile = await this.customerRepo.findByUserId(userId);
      isCustomer = true;
    } else {
      profile = await this.employeeRepo.findById(userId);
    }

    return {
      ...this._formatUserResponse(user, profile, permissions, isCustomer),
      isActive: user.is_active,
      lastLogin: user.last_login
    };
  }

  async posLogin({ employeeId, pin }) {
    if (!employeeId || !pin) {
      throw new ValidationError('Employee ID and PIN are required');
    }

    const userId = parseInt(employeeId);
    if (isNaN(userId)) throw new ValidationError('Employee ID must be a number');

    const user = await this.userRepo.findById(userId);
    if (!user) throw new UnauthorizedError('Invalid employee ID or PIN');
    if (!user.is_active) throw new UnauthorizedError('Account is inactive');

    const posAuth = await this.authRepo.findPosAuth(userId);
    if (!posAuth || !posAuth.is_enabled) {
      throw new UnauthorizedError('POS access not enabled for this account');
    }

    // Fetch security config from settings service (with fallback defaults)
    let maxAttempts = 5, lockMinutes = 30;
    try {
      const http = require('http');
      const config = await new Promise((resolve, reject) => {
        const req = http.get('http://settings:3004/api/internal/security-config', (res) => {
          let data = '';
          res.on('data', chunk => data += chunk);
          res.on('end', () => {
            try { resolve(JSON.parse(data)); } catch { resolve(null); }
          });
        });
        req.on('error', () => resolve(null));
        req.setTimeout(2000, () => { req.destroy(); resolve(null); });
      });
      if (config?.data) {
        maxAttempts = config.data.max_failed_attempts ?? maxAttempts;
        lockMinutes = config.data.lock_duration_minutes ?? lockMinutes;
      }
    } catch { /* Use defaults */ }

    // Check if account is locked
    if (posAuth.locked_until && new Date(posAuth.locked_until) > new Date()) {
      const minutesLeft = Math.ceil((new Date(posAuth.locked_until) - new Date()) / 60000);
      throw new PinLockedError(minutesLeft);
    }

    const valid = await bcrypt.compare(pin, posAuth.pin_hash);
    if (!valid) {
      const updated = await this.authRepo.incrementPosFailedAttempts(userId, maxAttempts, lockMinutes);
      const attemptsRemaining = Math.max(0, maxAttempts - (updated?.failed_attempts || 0));

      if (attemptsRemaining === 0) {
        const minutesLeft = lockMinutes;
        throw new PinLockedError(minutesLeft);
      }

      throw new PinInvalidError(attemptsRemaining);
    }

    await this.authRepo.resetPosFailedAttempts(userId);

    const permissions = await this.userRepo.getPermissions(userId);
    const employee = await this.employeeRepo.findById(userId);

    const token = generateToken({
      id: user.id, username: user.username,
      role: user.role_id,
      roleName: user.role_name || 'Employee',
      permissions,
      storeId: employee?.store_id || null,
      isPOS: true
    }, TOKEN_EXPIRY.POS);

    return {
      token,
      user: this._formatUserResponse(user, employee, permissions)
    };
  }

  /** @private */
  _formatUserResponse(user, profile, permissions, isCustomer = false) {
    const response = {
      id: user.id,
      username: user.username,
      email: user.email,
      fullName: profile?.full_name || user.username,
      phone: profile?.phone || '',
      address: profile?.address || '',
      dob: profile?.dob || null,
      storeId: !isCustomer ? (profile?.store_id || null) : null,
      role: user.role_name,
      permissions
    };
    // For Customer users, include customer table PK (different from user_account.id)
    if (isCustomer && profile) {
      response.customerId = profile.id;
    }
    return response;
  }
}

module.exports = AuthService;
