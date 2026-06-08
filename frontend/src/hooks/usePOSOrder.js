import { useState, useCallback } from 'react';
import posDataService from '../services/posDataService';

/**
 * POS Order Management Hook.
 * Handles checkout (draft creation), hold order, load held orders.
 */
export function usePOSOrder({ cart, setCart, selectedCustomer, setSelectedCustomer, showToast, parsePrice }) {
  const [existingOrder, setExistingOrder] = useState(null);
  const [showHeldOrdersModal, setShowHeldOrdersModal] = useState(false);
  const [holdLoading, setHoldLoading] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [loadingHeldOrder, setLoadingHeldOrder] = useState(false);

  // ========== CHANGE DETECTION ==========

  const hasCartChanged = useCallback(() => {
    if (!existingOrder || !existingOrder.details) return true;
    const orderDetails = existingOrder.details;

    if (cart.length !== orderDetails.length) return true;

    return cart.some(cartItem => {
      const cartProductId = cartItem.productId || cartItem.id;

      const matchingDetail = orderDetails.find(detail => {
        // Order microservice returns flat fields: detail.productId, detail.batchId
        if (cartItem.batch?.id) {
          return detail.productId === cartProductId && detail.batchId === cartItem.batch.id;
        }
        return detail.productId === cartProductId;
      });

      if (!matchingDetail) return true;
      return matchingDetail.quantity !== cartItem.quantity;
    });
  }, [existingOrder, cart]);

  const hasCustomerChanged = useCallback(() => {
    if (!existingOrder) return true;

    // Order microservice returns flat field: existingOrder.customerId (integer)
    const orderCustomerId = existingOrder.customerId;
    const selectedCustomerId = selectedCustomer?.id;

    // Both are guest → no change
    if ((!selectedCustomerId || selectedCustomerId === 'virtual-guest' || selectedCustomer?.customerType === 'guest') && !orderCustomerId) return false;

    // One is guest, other isn't → changed
    if (!selectedCustomerId || selectedCustomerId === 'virtual-guest' || selectedCustomer?.customerType === 'guest') {
      return !!orderCustomerId;
    }

    return orderCustomerId !== selectedCustomerId;
  }, [existingOrder, selectedCustomer]);

  // ========== HOLD ORDER ==========

  const handleHoldOrder = useCallback(async () => {
    if (cart.length === 0) {
      showToast('error', 'Cart is empty!');
      return;
    }

    try {
      setHoldLoading(true);

      const orderItems = cart.map(item => ({
        productId: item.productId || item.id,
        productName: item.name || 'Product',
        batchId: item.batch?.id || null,
        quantity: item.quantity,
        unitPrice: item.price
      }));

      const customerId = (!selectedCustomer?.id || selectedCustomer?.id === 'virtual-guest')
        ? null
        : selectedCustomer.id;

      const orderData = {
        customerId,
        items: orderItems,
        deliveryType: 'pickup',
        shippingFee: 0
      };

      const result = await posDataService.createOrder(orderData);

      if (!result.success && result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to hold order');
      }

      const order = result.data?.order || result.data;
      setCart([]);
      setSelectedCustomer(null);
      showToast('success', `Order ${order?.orderNumber || ''} saved as draft!`);
    } catch (error) {
      console.error('Error holding order:', error);
      showToast('error', error.message || 'Failed to hold order');
    } finally {
      setHoldLoading(false);
    }
  }, [cart, selectedCustomer, setCart, setSelectedCustomer, showToast]);

  // ========== CHECKOUT ==========

  const handleCheckout = useCallback(async () => {
    if (!cart || cart.length === 0) {
      showToast('error', 'Cart is empty!');
      return false;
    }

    if (!selectedCustomer) {
      showToast('error', 'Please select a customer!');
      return false;
    }

    // Existing order scenario (held order)
    if (existingOrder) {
      const cartChanged = hasCartChanged();
      const customerChanged = hasCustomerChanged();

      if (cartChanged || customerChanged) {
        console.log(`Order changed (Cart: ${cartChanged}, Customer: ${customerChanged}) - updating...`);

        try {
          setCheckoutLoading(true);

          const orderId = existingOrder.id;

          // Update items via updateDraftItems (FEFO re-allocation)
          if (cartChanged) {
            const items = cart.map(item => ({
              productId: item.productId || item.id,
              productName: item.name || 'Product',
              batchId: item.batch?.id || null,
              quantity: item.quantity,
              unitPrice: item.price
            }));

            const itemsResponse = await posDataService.updateDraftItems(orderId, items);

            if (!itemsResponse.success && itemsResponse.status !== 'success') {
              throw new Error(itemsResponse.error?.message || 'Failed to update order items');
            }
          }

          // Update customer if changed (send camelCase — backend maps it)
          if (customerChanged) {
            const customerId = selectedCustomer.id === 'virtual-guest' ? null : selectedCustomer.id;
            await posDataService.updateOrder(orderId, { customerId });
          }

          // Refresh the full order
          const refreshed = await posDataService.getOrderById(orderId);
          const updatedOrder = refreshed.data?.order || refreshed.data;
          updatedOrder.wasHeldOrder = existingOrder.wasHeldOrder;
          updatedOrder.vnpayProcessing = existingOrder.vnpayProcessing;
          setExistingOrder(updatedOrder);

          console.log('Held order updated:', updatedOrder.orderNumber);
          showToast('success', 'Order updated successfully');
        } catch (error) {
          console.error('Failed to update held order:', error);
          showToast('error', error.message || 'Failed to update order');
          return false;
        } finally {
          setCheckoutLoading(false);
        }
      }

      return true; // Signal to show payment modal
    }

    // New order scenario — create draft first
    console.log('Creating draft order before payment...');

    try {
      setCheckoutLoading(true);

      const items = cart.map(item => ({
        productId: item.productId || item.id,
        productName: item.name || 'Product',
        batchId: item.batch?.id || null,
        quantity: item.quantity,
        unitPrice: item.price
      }));

      const orderData = {
        customerId: (!selectedCustomer?.id || selectedCustomer.id === 'virtual-guest') ? null : selectedCustomer.id,
        items,
        deliveryType: 'pickup'
      };

      const result = await posDataService.createOrder(orderData);

      if (!result.success && result.status !== 'success') {
        throw new Error(result.error?.message || 'Failed to create order');
      }

      const draftOrder = result.data?.order || result.data;
      console.log('Draft order created:', draftOrder.orderNumber);

      draftOrder.wasHeldOrder = false;
      setExistingOrder(draftOrder);

      return true; // Signal to show payment modal
    } catch (error) {
      console.error('Failed to create draft order:', error);
      showToast('error', error.message);
      return false;
    } finally {
      setCheckoutLoading(false);
    }
  }, [cart, selectedCustomer, existingOrder, hasCartChanged, hasCustomerChanged, showToast]);

  // ========== LOAD HELD ORDER ==========

  const handleLoadHeldOrder = useCallback(async (order) => {
    try {
      if (cart.length > 0) {
        const confirm = window.confirm('Current cart will be cleared. Do you want to continue?');
        if (!confirm) return;
      }

      setCart([]);
      setLoadingHeldOrder(true);

      // Fetch customer data from Auth API (microservice returns flat customerId)
      if (order.customerId && order.customerId !== 'virtual-guest') {
        try {
          const customerRes = await posDataService.getCustomerById(order.customerId);
          const cust = customerRes.data?.customer || customerRes.data;
          if (cust) {
            setSelectedCustomer({
              id: cust.id,
              customerCode: cust.customerCode || cust.customer_code,
              fullName: cust.fullName || cust.full_name,
              phone: cust.phone,
              customerType: cust.customerType || cust.customer_type || 'guest'
            });
          } else {
            setSelectedCustomer(null);
          }
        } catch (err) {
          console.warn('Failed to fetch customer info:', err.message);
          setSelectedCustomer(null);
        }
      } else {
        // Fetch default guest customer!
        try {
          const guestRes = await posDataService.getDefaultGuest();
          const guest = guestRes.data?.customer || guestRes.data;
          setSelectedCustomer(guest);
        } catch (err) {
          console.warn('Failed to fetch default guest customer:', err.message);
          setSelectedCustomer(null);
        }
      }

      order.wasHeldOrder = true;

      // Enrich product details from Catalog API (need isPerishable + image)
      const details = order.details || [];
      const uniqueProductIds = [...new Set(details.map(d => d.productId).filter(Boolean))];

      // Batch fetch product info using Promise.all
      const productMap = {};
      if (uniqueProductIds.length > 0) {
        const productResults = await Promise.all(
          uniqueProductIds.map(pid =>
            posDataService.getProductById(pid).catch(() => null)
          )
        );

        productResults.forEach(res => {
          if (res) {
            const prod = res.data?.product || res.data;
            if (prod) {
              productMap[prod.id] = prod;
            }
          }
        });
      }

      // Convert order details to cart items using flat fields
      const cartItems = [];

      for (const detail of details) {
        const productId = detail.productId;
        const batchId = detail.batchId;
        const unitPrice = parsePrice(detail.unitPrice);
        const productName = detail.productName || 'Product';

        // Enriched product data from Catalog API
        const enrichedProduct = productMap[productId] || {};
        const isFresh = enrichedProduct.isPerishable ||
          enrichedProduct.category?.isPerishable ||
          enrichedProduct.category?.is_perishable || false;

        const cartItem = {
          id: (isFresh && batchId) ? `${productId}-${batchId}` : `${productId}`,
          productId: productId,
          productCode: enrichedProduct.productCode || enrichedProduct.product_code || '',
          name: productName,
          image: enrichedProduct.image || '',
          price: unitPrice,
          quantity: detail.quantity,
          stock: 999,
          categoryName: enrichedProduct.category?.name || 'Uncategorized'
        };

        // For fresh products with batch: attach batch info from enriched product
        if (isFresh && batchId) {
          // Try to get batch details from the enriched product or use flat values
          cartItem.batch = {
            id: batchId,
            batchCode: `BATCH-${batchId}`,
            unitPrice: unitPrice,
            discountPercentage: 0
          };

          // Attempt to enrich batch details from inventory
          try {
            const batchesRes = await posDataService.getProductBatches(productId);
            const batches = batchesRes.data || [];
            const matchedBatch = batches.find(b => b.id === batchId || b.id === String(batchId));
            if (matchedBatch) {
              cartItem.batch = {
                id: matchedBatch.id,
                batchCode: matchedBatch.batchCode,
                expiryDate: matchedBatch.expiryDate,
                unitPrice: parsePrice(matchedBatch.unitPrice) || unitPrice,
                discountPercentage: matchedBatch.discountPercentage || 0,
                availableQty: matchedBatch.totalOnShelf || matchedBatch.quantity || 999
              };
              // Recalculate price with batch discount
              if (cartItem.batch.discountPercentage > 0) {
                const basePrice = parsePrice(cartItem.batch.unitPrice);
                cartItem.price = basePrice * (1 - cartItem.batch.discountPercentage / 100);
              }
            }
          } catch (_) {
            // Batch enrichment failed — use flat values from order detail
          }
        } else {
          // Regular product — apply discount info from enriched product
          const productUnitPrice = parsePrice(enrichedProduct.unitPrice || enrichedProduct.unit_price);
          const productDiscount = enrichedProduct.discountPercentage || 0;

          if (productDiscount > 0 && productUnitPrice > 0) {
            cartItem.basePrice = productUnitPrice;
            cartItem.discountPercentage = productDiscount;
          } else if (productUnitPrice > unitPrice && productUnitPrice > 0) {
            cartItem.basePrice = productUnitPrice;
            cartItem.discountPercentage = Math.round(((productUnitPrice - unitPrice) / productUnitPrice) * 100);
          }
        }

        cartItems.push(cartItem);
      }

      setCart(cartItems);
      setExistingOrder({ ...order, id: order.id });
      showToast('success', `Loaded order ${order.orderNumber} to cart`);
    } catch (error) {
      console.error('Error loading held order:', error);
      showToast('error', 'Failed to load order');
    } finally {
      setLoadingHeldOrder(false);
    }
  }, [cart, setCart, setSelectedCustomer, showToast, parsePrice]);

  return {
    holdLoading,
    checkoutLoading,
    loadingHeldOrder,
    existingOrder,
    setExistingOrder,
    showHeldOrdersModal,
    setShowHeldOrdersModal,
    handleHoldOrder,
    handleCheckout,
    handleLoadHeldOrder
  };
}
