import { useState, useCallback } from 'react';

/**
 * POS Cart Management Hook.
 * Handles cart CRUD, stock validation, price calculation, batch products, totals.
 */
export function usePOSCart({ customerDiscounts, selectedCustomer, showToast }) {
  const [cart, setCart] = useState([]);
  const [lastAddedId, setLastAddedId] = useState(null);

  // ========== PRICE HELPERS ==========

  const parsePrice = useCallback((price) => {
    if (!price && price !== 0) return 0;
    if (typeof price === 'object' && price !== null) {
      if (price.$numberDecimal) return parseFloat(price.$numberDecimal);
      if (price.toString) return parseFloat(price.toString());
    }
    const parsed = parseFloat(price);
    return isNaN(parsed) ? 0 : parsed;
  }, []);

  const getBatchPrice = useCallback((batch) => {
    if (!batch) return 0;
    const price = batch.unitPrice;
    if (price === null || price === undefined) return 0;
    if (typeof price === 'object' && price !== null) {
      if (price.$numberDecimal) return parseFloat(price.$numberDecimal);
      return parseFloat(price.toString());
    }
    const parsed = parseFloat(price);
    return isNaN(parsed) ? 0 : parsed;
  }, []);

  const getBatchDiscountPercentage = useCallback((batch) => {
    if (!batch) return 0;
    return batch.discountPercentage || 0;
  }, []);

  const getCurrentBatchPrice = useCallback((batch) => {
    if (!batch) return 0;
    const basePrice = getBatchPrice(batch);
    const discountPercentage = getBatchDiscountPercentage(batch);
    if (discountPercentage > 0) {
      return basePrice * (1 - discountPercentage / 100);
    }
    return basePrice;
  }, [getBatchPrice, getBatchDiscountPercentage]);

  // ========== ADD TO CART (regular product) ==========

  const addToCart = useCallback(async (product) => {
    const isFresh = product.isPerishable || product.category?.isPerishable || product.category?.is_perishable || false;

    if (isFresh) {
      // Return product data for batch modal — caller handles the modal
      return { needsBatchSelection: true, product };
    }

    // REGULAR PRODUCT: Add directly to cart
    const availableStock = product.stock || product.inventory?.quantityAvailable || 0;
    const onShelfQuantity = product.inventory?.quantityOnShelf || 0;

    if (onShelfQuantity <= 0) {
      showToast('error', `${product.name} is not available on shelf!`);
      return { needsBatchSelection: false };
    }

    const basePrice = product.unitPrice || product.price || 0;
    const discountPercentage = product.discountPercentage || 0;
    const finalPrice = discountPercentage > 0
      ? basePrice * (1 - discountPercentage / 100)
      : basePrice;

    setCart(prevCart => {
      const normalizedId = product._id || product.id;
      const existingItem = prevCart.find(item => item.id === normalizedId);
      const currentQuantityInCart = existingItem ? existingItem.quantity : 0;

      if (currentQuantityInCart >= availableStock) {
        showToast('error', `Not enough stock. Available: ${availableStock}`);
        return prevCart;
      }

      if (existingItem) {
        showToast('success', `Updated ${product.name} quantity`);
        return prevCart.map(item =>
          item.id === normalizedId
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      } else {
        showToast('success', `Added ${product.name} to cart`);
        return [...prevCart, {
          ...product,
          id: normalizedId,
          productId: normalizedId,
          quantity: 1,
          basePrice,
          discountPercentage,
          price: finalPrice
        }];
      }
    });

    // Trigger highlight on the cart item
    const itemId = product._id || product.id;
    setLastAddedId(`${itemId}-${Date.now()}`);
    // Use a stable id for the DOM lookup
    setTimeout(() => setLastAddedId(itemId), 10);

    return { needsBatchSelection: false };
  }, [showToast]);

  // ========== ADD WITH BATCH (fresh product) ==========

  const addProductWithBatch = useCallback((productData, batch, quantity) => {
    const { product, inventory } = productData;
    const batchId = batch.id || batch._id;
    const cartItemId = `${product.id}-${batchId}`;
    const batchPrice = getCurrentBatchPrice(batch);

    const cartItem = {
      id: cartItemId,
      productId: product.id,
      productCode: product.productCode,
      name: product.name,
      image: product.image,
      price: batchPrice,
      quantity,
      stock: batch.quantity || inventory?.quantityAvailable || 0,
      categoryName: product.category?.name || 'Uncategorized',
      batch: {
        id: batchId,
        batchCode: batch.batchCode,
        expiryDate: batch.expiryDate,
        availableQty: batch.quantity,
        daysUntilExpiry: batch.daysUntilExpiry,
        unitPrice: getBatchPrice(batch),
        discountPercentage: getBatchDiscountPercentage(batch)
      }
    };

    setCart(prevCart => {
      const existingItem = prevCart.find(item => item.id === cartItemId);

      if (existingItem) {
        const newQuantity = existingItem.quantity + quantity;
        const maxQty = batch.quantity;

        if (newQuantity > maxQty) {
          showToast('error', `Not enough stock for batch ${batch.batchCode}. Available: ${maxQty}`);
          return prevCart;
        }

        showToast('success', `Updated ${product.name} (${batch.batchCode}) quantity to ${newQuantity}`);
        return prevCart.map(item =>
          item.id === cartItemId
            ? { ...item, quantity: newQuantity }
            : item
        );
      } else {
        showToast('success', `Added ${quantity}x ${product.name} (${batch.batchCode}) to cart`);
        return [...prevCart, cartItem];
      }
    });

    // Trigger cart highlight
    setLastAddedId(`${cartItemId}-${Date.now()}`);
    setTimeout(() => setLastAddedId(cartItemId), 10);
  }, [getCurrentBatchPrice, getBatchPrice, getBatchDiscountPercentage, showToast]);

  // ========== CART CRUD ==========

  const updateQuantity = useCallback((productId, newQuantity) => {
    if (newQuantity <= 0) {
      setCart(prevCart => prevCart.filter(item => item.id !== productId));
      return;
    }

    setCart(prevCart => {
      const cartItem = prevCart.find(item => item.id === productId);
      if (!cartItem) return prevCart;

      const availableStock = cartItem.batch?.availableQty || cartItem.stock || cartItem.inventory?.quantityAvailable || 0;
      if (newQuantity > availableStock) {
        showToast('error', `Not enough stock. Available: ${availableStock}`);
        return prevCart;
      }

      return prevCart.map(item =>
        item.id === productId
          ? { ...item, quantity: newQuantity }
          : item
      );
    });
  }, [showToast]);

  const removeFromCart = useCallback((productId) => {
    setCart(prevCart => prevCart.filter(item => item.id !== productId));
  }, []);

  const clearCart = useCallback(() => {
    if (window.confirm('Clear all items from cart?')) {
      setCart([]);
      return true; // Signal to caller to also clear existingOrder
    }
    return false;
  }, []);

  // ========== TOTALS ==========

  const calculateTotals = useCallback(() => {
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const discountPercentage = selectedCustomer
      ? (customerDiscounts[selectedCustomer.customerType] || 0)
      : 0;
    const discount = subtotal * (discountPercentage / 100);
    const shippingFee = 0;
    const total = subtotal - discount + shippingFee;

    return { subtotal, discount, discountPercentage, shippingFee, total };
  }, [cart, selectedCustomer, customerDiscounts]);

  return {
    cart,
    setCart,
    lastAddedId,
    addToCart,
    addProductWithBatch,
    updateQuantity,
    removeFromCart,
    clearCart,
    calculateTotals,
    parsePrice
  };
}
