/**
 * Action Types Constants for Chatbot Action Assistant
 * Used by backend database handlers and client-side dispatch.
 */

const ACTION_TYPES = {
  ADD_TO_CART: 'ADD_TO_CART',
  REMOVE_FROM_CART: 'REMOVE_FROM_CART',
  UPDATE_CART_ITEM: 'UPDATE_CART_ITEM',
  VIEW_CART: 'VIEW_CART',
  POS_ADD_ITEM: 'POS_ADD_ITEM',
  CREATE_ORDER: 'CREATE_ORDER',
  CANCEL_ORDER: 'CANCEL_ORDER',
  UPDATE_ORDER: 'UPDATE_ORDER',
  PAYMENT_CHECK: 'PAYMENT_CHECK',
  TRACK_ORDER: 'TRACK_ORDER',
  CHECKOUT_GUIDE: 'CHECKOUT_GUIDE',
  NAVIGATE: 'NAVIGATE'
};

// Actions that mutate state/database on server-side and require user confirmation first
const CONFIRM_REQUIRED = [
  ACTION_TYPES.CREATE_ORDER,
  ACTION_TYPES.CANCEL_ORDER,
  ACTION_TYPES.UPDATE_ORDER
];

module.exports = {
  ACTION_TYPES,
  CONFIRM_REQUIRED
};
