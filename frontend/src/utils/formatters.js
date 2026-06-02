/**
 * Utility functions for formatting database identifier codes
 */

/**
 * Safely format customer code, falling back to CUST-id or GUEST.
 * @param {object} customer
 * @returns {string}
 */
export function formatCustomerCode(customer) {
  if (!customer) return 'GUEST';
  return (
    customer.customerCode ||
    customer.customer_code ||
    (customer.customerId || customer.id || customer.customer_id
      ? `CUST-${customer.customerId || customer.id || customer.customer_id}`
      : 'GUEST')
  );
}

/**
 * Safely format employee code, falling back to EMP-id.
 * @param {object} employee
 * @returns {string}
 */
export function formatEmployeeCode(employee) {
  if (!employee) return 'N/A';
  return (
    employee.employeeCode ||
    employee.employee_code ||
    (employee.employeeId || employee.id || employee.user_id
      ? `EMP-${employee.employeeId || employee.id || employee.user_id}`
      : 'N/A')
  );
}

/**
 * Safely format product identifier, prioritizing barcode, then productCode, then PROD-id.
 * @param {object} product
 * @returns {string}
 */
export function formatProductCode(product) {
  if (!product) return 'N/A';
  return (
    product.barcode ||
    product.productCode ||
    product.product_code ||
    (product.productId || product.id || product.product_id
      ? `PROD-${product.productId || product.id || product.product_id}`
      : 'N/A')
  );
}
