import { createContext, useContext, useState, useCallback, useEffect, useRef } from "react";
import { useStore } from "./StoreContext";
import toast from "react-hot-toast";

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const { selectedStore } = useStore();
  
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

  const [isCartOpen, setIsCartOpen] = useState(false);
  const cartTimerRef = useRef(null);

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

  const addToCart = useCallback((product) => {
    setCartItems((prevItems) => {
      const existingItem = prevItems.find((item) => item.id === product.id);

      if (existingItem) {
        return prevItems.map((item) =>
          item.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }

      return [...prevItems, { ...product, quantity: 1 }];
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
  }, []);

  const getCartTotal = useCallback(() => {
    return cartItems.reduce(
      (total, item) => total + item.price * item.quantity,
      0
    );
  }, [cartItems]);

  const getCartDiscount = useCallback(() => {
    if (!appliedCoupon) return 0;
    const subtotal = getCartTotal();
    if (appliedCoupon.type === 'percent') {
      return subtotal * (appliedCoupon.value / 100);
    }
    return appliedCoupon.value;
  }, [appliedCoupon, getCartTotal]);

  const applyCoupon = useCallback((code) => {
    // Mock Validation for Task 15
    const upperCode = code.toUpperCase();
    if (upperCode === 'WELCOME10') {
      setAppliedCoupon({ code: upperCode, type: 'percent', value: 10, description: '10% off your order' });
      toast.success('Coupon WELCOME10 applied!');
      return true;
    }
    if (upperCode === 'FREESHIP50') {
      setAppliedCoupon({ code: upperCode, type: 'fixed', value: 50000, description: '50,000 VND off' });
      toast.success('Coupon FREESHIP50 applied!');
      return true;
    }
    if (upperCode === 'EXPIRED') {
      toast.error('Coupon has expired');
      return false;
    }
    
    toast.error('Invalid coupon code');
    return false;
  }, []);

  const removeCoupon = useCallback(() => {
    setAppliedCoupon(null);
    toast.success('Coupon removed');
  }, []);

  const getCartCount = useCallback(() => {
    return cartItems.reduce((count, item) => count + item.quantity, 0);
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
    addMultipleToCart
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
