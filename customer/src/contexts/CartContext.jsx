import { createContext, useContext, useState, useCallback, useEffect, useRef } from "react";
import { useStore } from "./StoreContext";
import { useAuth } from "./AuthContext";
import couponService from "../services/couponService";
import toast from "react-hot-toast";

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const { selectedStore } = useStore();
  const { user } = useAuth();

  const [cartItems, setCartItems] = useState(() => {
    // If no store selected, start empty
    if (!selectedStore?.id) return [];

    try {
      const saved = localStorage.getItem(`cart_${selectedStore.id}`);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [appliedCoupon, setAppliedCoupon] = useState(() => {
    try {
      const saved = localStorage.getItem(`coupon_${selectedStore?.id}`);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [discountRates, setDiscountRates] = useState({ retail: 0, wholesale: 5, vip: 10 });
  const [deliveryType, setDeliveryType] = useState('delivery'); // 'delivery' or 'pickup'
  const [isCartOpen, setIsCartOpen] = useState(false);
  const cartTimerRef = useRef(null);

  // Fetch discount rates from backend
  useEffect(() => {
    const fetchDiscounts = async () => {
      try {
        const res = await couponService.getCustomerDiscounts();
        if (res.success && res.data) {
          setDiscountRates(res.data);
        }
      } catch (err) {
        console.error("Failed to fetch customer discount settings:", err);
      }
    };
    fetchDiscounts();
  }, []);

  const keepCartOpen = useCallback(() => {
    if (cartTimerRef.current) {
      clearTimeout(cartTimerRef.current);
    }
  }, []);

  const resumeCartTimer = useCallback(() => {
    if (cartTimerRef.current) {
      clearTimeout(cartTimerRef.current);
    }
    cartTimerRef.current = setTimeout(() => {
      setIsCartOpen(false);
    }, 4000);
  }, []);

  const openCartTemporarily = useCallback(() => {
    setIsCartOpen(true);
    resumeCartTimer();
  }, [resumeCartTimer]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (cartTimerRef.current) clearTimeout(cartTimerRef.current);
    };
  }, []);

  // When store changes, load its cart
  useEffect(() => {
    if (!selectedStore?.id) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCartItems([]);
      return;
    }
    try {
      const saved = localStorage.getItem(`cart_${selectedStore.id}`);
      if (saved) {
        setCartItems(JSON.parse(saved));
      } else {
        setCartItems([]);
      }
    } catch {
      setCartItems([]);
    }
  }, [selectedStore?.id]);

  // When cart changes, save it
  useEffect(() => {
    if (selectedStore?.id) {
      localStorage.setItem(`cart_${selectedStore.id}`, JSON.stringify(cartItems));
    }
  }, [cartItems, selectedStore?.id]);

  // When coupon changes, save it
  useEffect(() => {
    if (selectedStore?.id) {
      if (appliedCoupon) {
        localStorage.setItem(`coupon_${selectedStore.id}`, JSON.stringify(appliedCoupon));
      } else {
        localStorage.removeItem(`coupon_${selectedStore.id}`);
      }
    }
  }, [appliedCoupon, selectedStore?.id]);

  const addToCart = useCallback((product, qty = 1) => {
    setCartItems((prevItems) => {
      const existingItem = prevItems.find((item) => item.id === product.id);

      if (existingItem) {
        return prevItems.map((item) =>
          item.id === product.id
            ? { ...item, quantity: item.quantity + qty }
            : item
        );
      }

      return [...prevItems, { ...product, quantity: qty }];
    });

    toast.success(`${product.name} added to cart`);
    openCartTemporarily();
  }, [openCartTemporarily]);

  const addMultipleToCart = useCallback(async (items, inventoryMap) => {
    let addedCount = 0;

    setCartItems((prevItems) => {
      const newItems = [...prevItems];

      items.forEach((newItem) => {
        const existingIndex = newItems.findIndex((item) => item.id === newItem.id);
        const currentQty = existingIndex >= 0 ? newItems[existingIndex].quantity : 0;
        const available = inventoryMap[newItem.id] || 0;

        // Target quantity
        let targetQty = currentQty + newItem.quantity;

        // Cap at inventory
        if (targetQty > available) {
          targetQty = available;
        }

        const addedQty = targetQty - currentQty;

        if (addedQty > 0) {
          addedCount += addedQty;
          if (existingIndex >= 0) {
            newItems[existingIndex] = { ...newItems[existingIndex], quantity: targetQty };
          } else {
            newItems.push({ ...newItem, quantity: targetQty });
          }
        }
      });

      return newItems;
    });

    if (addedCount > 0) {
      toast.success(`${addedCount} items added to cart`);
      openCartTemporarily();
    } else {
      toast.error('Products are out of stock');
    }
  }, [openCartTemporarily]);

  const removeFromCart = useCallback((productId) => {
    setCartItems((prevItems) =>
      prevItems.filter((item) => item.id !== productId)
    );
  }, []);

  const updateQuantity = useCallback((productId, newQuantity) => {
    if (newQuantity <= 0) {
      setCartItems((prevItems) =>
        prevItems.filter((item) => item.id !== productId)
      );
      return;
    }

    setCartItems((prevItems) =>
      prevItems.map((item) =>
        item.id === productId ? { ...item, quantity: newQuantity } : item
      )
    );
  }, []);

  const clearCart = useCallback(() => {
    setCartItems([]);
    setAppliedCoupon(null);
  }, []);

  // 1. Raw Subtotal
  const getCartTotal = useCallback(() => {
    return cartItems.reduce(
      (total, item) => total + item.price * item.quantity,
      0
    );
  }, [cartItems]);

  // 2. Membership Discount Rate
  const getMembershipDiscountRate = useCallback(() => {
    const type = user?.customerType || user?.customer_type || 'retail';
    return parseFloat(discountRates[type.toLowerCase()] ?? 0);
  }, [user, discountRates]);

  // 3. Membership Discount Amount
  const getMembershipDiscount = useCallback(() => {
    return getCartTotal() * (getMembershipDiscountRate() / 100);
  }, [getCartTotal, getMembershipDiscountRate]);

  // 4. Subtotal after Membership Discount
  const getSubtotalAfterMember = useCallback(() => {
    return getCartTotal() - getMembershipDiscount();
  }, [getCartTotal, getMembershipDiscount]);

  // 5. Coupon Discount Amount (applied only to subtotal)
  const getCartDiscount = useCallback(() => {
    if (!appliedCoupon) return 0;
    const base = getSubtotalAfterMember();

    // Support both backend fields (discount_type, discount_value) and legacy mock (type, value)
    const type = appliedCoupon.discount_type || appliedCoupon.type;
    const value = appliedCoupon.discount_value !== undefined ? appliedCoupon.discount_value : appliedCoupon.value;

    if (type === 'percent') {
      return Math.min(base, base * (parseFloat(value) / 100));
    }
    if (type === 'fixed') {
      return Math.min(base, parseFloat(value));
    }
    return 0; // freeship discount is applied to shipping fee, not subtotal
  }, [appliedCoupon, getSubtotalAfterMember]);

  const getSubtotalAfterCoupon = useCallback(() => {
    return getSubtotalAfterMember() - getCartDiscount();
  }, [getSubtotalAfterMember, getCartDiscount]);

  // 6. Online Shipping Fee (default to 30000 VND for delivery, 0 for pickup)
  const getShippingFee = useCallback(() => {
    return deliveryType === 'delivery' ? 30000 : 0;
  }, [deliveryType]);

  // 7. Shipping Coupon Discount
  const getShippingDiscount = useCallback(() => {
    if (!appliedCoupon) return 0;
    const type = appliedCoupon.discount_type || appliedCoupon.type;
    const value = appliedCoupon.discount_value !== undefined ? appliedCoupon.discount_value : appliedCoupon.value;

    if (type === 'freeship') {
      return Math.min(getShippingFee(), parseFloat(value));
    }
    return 0;
  }, [appliedCoupon, getShippingFee]);

  // 8. Net Total Amount
  const getTotalAmount = useCallback(() => {
    return getSubtotalAfterCoupon() + (getShippingFee() - getShippingDiscount());
  }, [getSubtotalAfterCoupon, getShippingFee, getShippingDiscount]);

  const applyCoupon = useCallback(async (code) => {
    if (!code) {
      toast.error('Coupon code is required');
      return false;
    }
    try {
      const base = getSubtotalAfterMember();
      const res = await couponService.validateCoupon(code, base);
      if (res.success && res.data?.valid) {
        const coupon = res.data.coupon;
        // Map fields for backward compatibility
        const normalized = {
          ...coupon,
          type: coupon.discount_type,
          value: coupon.discount_value
        };
        setAppliedCoupon(normalized);
        toast.success(`Coupon ${coupon.code} applied successfully!`);
        return true;
      } else {
        toast.error(res.data?.error || 'Invalid coupon code');
        return false;
      }
    } catch (err) {
      console.error('Error applying coupon:', err);
      toast.error('Failed to validate coupon code');
      return false;
    }
  }, [getSubtotalAfterMember]);

  const removeCoupon = useCallback(() => {
    setAppliedCoupon(null);
    toast.success('Coupon removed');
  }, []);

  const getCartCount = useCallback(() => {
    return cartItems.length;
  }, [cartItems]);

  const value = {
    cartItems,
    addToCart,
    removeFromCart,
    updateQuantity,
    clearCart,
    getCartTotal,
    getCartCount,
    isCartOpen,
    setIsCartOpen,
    openCartTemporarily,
    keepCartOpen,
    resumeCartTimer,
    appliedCoupon,
    applyCoupon,
    removeCoupon,
    getCartDiscount,
    addMultipleToCart,
    // New omnichannel discount exports
    discountPercentage: getMembershipDiscountRate(),
    getMembershipDiscount,
    getSubtotalAfterMember,
    deliveryType,
    setDeliveryType,
    getShippingFee,
    getShippingDiscount,
    getTotalAmount
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return context;
}

