import { Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { X, ShoppingCart, Trash2, Plus, Minus } from 'lucide-react';
import { useCart } from '../../contexts/CartContext';
import { Link, useNavigate } from 'react-router-dom';

export const CartDrawer = () => {
  const { 
    cartItems, 
    isCartOpen, 
    setIsCartOpen, 
    keepCartOpen, 
    resumeCartTimer,
    removeFromCart,
    updateQuantity,
    getCartTotal
  } = useCart();
  const navigate = useNavigate();

  const formatVND = (amount) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND' }).format(amount);

  const handleCheckout = () => {
    setIsCartOpen(false);
    navigate('/checkout');
  };

  return (
    <Transition.Root show={isCartOpen} as={Fragment}>
      <Dialog 
        as="div" 
        className="relative z-50" 
        onClose={setIsCartOpen}
      >
        <Transition.Child
          as={Fragment}
          enter="ease-in-out duration-500"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in-out duration-500"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
              <Transition.Child
                as={Fragment}
                enter="transform transition ease-in-out duration-500 sm:duration-700"
                enterFrom="translate-x-full"
                enterTo="translate-x-0"
                leave="transform transition ease-in-out duration-500 sm:duration-700"
                leaveFrom="translate-x-0"
                leaveTo="translate-x-full"
              >
                <Dialog.Panel 
                  className="pointer-events-auto w-screen max-w-md"
                  onMouseEnter={keepCartOpen}
                  onMouseLeave={resumeCartTimer}
                >
                  <div className="flex h-full flex-col bg-white shadow-2xl">
                    <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
                      <div className="flex items-start justify-between">
                        <Dialog.Title className="text-lg font-bold text-gray-900 flex items-center gap-2">
                          <ShoppingCart className="w-5 h-5 text-emerald-600" />
                          Shopping Cart
                        </Dialog.Title>
                        <div className="ml-3 flex h-7 items-center">
                          <button
                            type="button"
                            className="relative -m-2 p-2 text-gray-400 hover:text-gray-500"
                            onClick={() => setIsCartOpen(false)}
                          >
                            <span className="absolute -inset-0.5" />
                            <span className="sr-only">Close panel</span>
                            <X className="h-6 w-6" aria-hidden="true" />
                          </button>
                        </div>
                      </div>

                      <div className="mt-8">
                        <div className="flow-root">
                          {cartItems.length === 0 ? (
                            <div className="text-center py-12">
                              <div className="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
                                <ShoppingCart className="h-10 w-10 text-gray-300" />
                              </div>
                              <h3 className="text-sm font-medium text-gray-900">Your cart is empty</h3>
                              <p className="mt-1 text-sm text-gray-500">
                                Start adding some items to your cart!
                              </p>
                              <div className="mt-6">
                                <button
                                  type="button"
                                  onClick={() => setIsCartOpen(false)}
                                  className="text-sm font-medium text-emerald-600 hover:text-emerald-500"
                                >
                                  Continue Shopping &rarr;
                                </button>
                              </div>
                            </div>
                          ) : (
                            <ul role="list" className="-my-6 divide-y divide-gray-100">
                              {cartItems.map((item) => (
                                <li key={item.id} className="flex py-6 group">
                                  <div className="h-24 w-24 flex-shrink-0 overflow-hidden rounded-xl border border-gray-100 bg-gray-50 p-2">
                                    <img
                                      src={item.image || 'https://via.placeholder.com/150'}
                                      alt={item.name}
                                      className="h-full w-full object-contain object-center mix-blend-multiply"
                                    />
                                  </div>

                                  <div className="ml-4 flex flex-1 flex-col">
                                    <div>
                                      <div className="flex justify-between text-base font-medium text-gray-900">
                                        <h3 className="line-clamp-2 text-sm">
                                          <Link to={`/product/${item.id}`} onClick={() => setIsCartOpen(false)} className="hover:text-emerald-600">
                                            {item.name}
                                          </Link>
                                        </h3>
                                        <p className="ml-4 whitespace-nowrap text-emerald-600 font-bold text-sm">
                                          {formatVND(item.price * item.quantity)}
                                        </p>
                                      </div>
                                    </div>
                                    <div className="flex flex-1 items-end justify-between text-sm">
                                      <div className="flex items-center gap-2 bg-gray-50 rounded-lg p-1 border border-gray-100">
                                        <button 
                                          type="button"
                                          onClick={() => updateQuantity(item.id, item.quantity - 1)}
                                          className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-emerald-600 hover:bg-white rounded shadow-sm transition-all disabled:opacity-50"
                                          disabled={item.quantity <= 1}
                                        >
                                          <Minus className="w-3 h-3" />
                                        </button>
                                        <span className="w-6 text-center font-semibold text-gray-700 text-xs">{item.quantity}</span>
                                        <button 
                                          type="button"
                                          onClick={() => updateQuantity(item.id, item.quantity + 1)}
                                          className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-emerald-600 hover:bg-white rounded shadow-sm transition-all"
                                        >
                                          <Plus className="w-3 h-3" />
                                        </button>
                                      </div>

                                      <div className="flex">
                                        <button
                                          type="button"
                                          onClick={() => removeFromCart(item.id)}
                                          className="font-medium text-red-500 hover:text-red-600 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                          <Trash2 className="w-4 h-4" />
                                          <span className="sr-only">Remove</span>
                                        </button>
                                      </div>
                                    </div>
                                  </div>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </div>
                    </div>

                    {cartItems.length > 0 && (
                      <div className="border-t border-gray-100 bg-gray-50 px-4 py-6 sm:px-6">
                        <div className="flex justify-between text-base font-bold text-gray-900 mb-4">
                          <p>Subtotal</p>
                          <p className="text-emerald-600 text-xl">{formatVND(getCartTotal())}</p>
                        </div>
                        <p className="mt-0.5 text-sm text-gray-500 mb-6">
                          Shipping and taxes calculated at checkout.
                        </p>
                        <div className="grid grid-cols-2 gap-4">
                          <button
                            type="button"
                            onClick={() => {
                              setIsCartOpen(false);
                              navigate('/cart');
                            }}
                            className="flex items-center justify-center rounded-xl border border-emerald-500 bg-white px-6 py-3 text-sm font-semibold text-emerald-600 shadow-sm hover:bg-emerald-50 transition-colors"
                          >
                            View Cart
                          </button>
                          <button
                            type="button"
                            onClick={handleCheckout}
                            className="flex items-center justify-center rounded-xl border border-transparent bg-emerald-500 px-6 py-3 text-sm font-semibold text-white shadow-sm shadow-emerald-200 hover:bg-emerald-600 transition-colors"
                          >
                            Checkout
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
};
